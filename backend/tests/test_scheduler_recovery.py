"""Reportes y cron en una transacción: reintentos, interrupción y competencia."""
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.endpoints import reports
from app.core import database
from app.core.config import settings
from app.models.models import Base, Report, ReportSchedule, User, UserRole
from app.services.report_data_service import utc
from app.services.report_scheduler_service import run_due_reports


@pytest.fixture
async def scheduler_db(tmp_path, monkeypatch):
    engine = create_async_engine(f'sqlite+aiosqlite:///{(tmp_path / "scheduler.db").as_posix()}')
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(database, 'AsyncSessionLocal', sessions)
    monkeypatch.setattr(settings, 'REPORTS_DIR', str(tmp_path / 'reports'))
    async with sessions() as db:
        user = User(username='scheduler_qa', email='qa@example.test', first_name='QA', last_name='Scheduler',
                    password_hash='unused-test-only', role=UserRole.ADMIN, is_active=True)
        db.add(user)
        await db.flush()
        user_id = user.id
        await db.commit()
    yield sessions, user_id
    await engine.dispose()


async def add_schedule(sessions, user_id, name='QA scheduled report'):
    due = datetime.now(timezone.utc) - timedelta(minutes=2)
    async with sessions() as db:
        item = ReportSchedule(name=name, report_type='detections', format='csv', cron_expr='* * * * *',
                              is_active=True, created_by=user_id, next_run=due)
        db.add(item)
        await db.commit()
        return item.id, due


async def assert_pending(sessions, schedule_id, due):
    async with sessions() as db:
        item = await db.get(ReportSchedule, schedule_id)
        assert utc(item.next_run) == due
        assert item.last_run is None


async def assert_one_report(sessions, schedule_id, due):
    async with sessions() as db:
        item = await db.get(ReportSchedule, schedule_id)
        assert utc(item.next_run) > due
        assert item.last_run is not None
        rows = (await db.execute(select(Report))).scalars().all()
        assert len(rows) == 1
        path = Path(settings.REPORTS_DIR) / rows[0].params['storage_name']
        assert path.is_file()


async def test_generation_failure_remains_due_and_recovers(scheduler_db, monkeypatch):
    sessions, user_id = scheduler_db
    schedule_id, due = await add_schedule(sessions, user_id)
    original = reports.compile_report
    def fail(*args):
        raise RuntimeError('Simulated generation failure')
    monkeypatch.setattr(reports, 'compile_report', fail)
    assert await run_due_reports() == 0
    await assert_pending(sessions, schedule_id, due)
    monkeypatch.setattr(reports, 'compile_report', original)
    assert await run_due_reports() == 1
    assert await run_due_reports() == 0
    await assert_one_report(sessions, schedule_id, due)


async def test_interruption_after_claim_rolls_back(scheduler_db, monkeypatch):
    sessions, user_id = scheduler_db
    schedule_id, due = await add_schedule(sessions, user_id)
    original = reports.persist_report
    async def interrupt(*args):
        raise asyncio.CancelledError()
    monkeypatch.setattr(reports, 'persist_report', interrupt)
    with pytest.raises(asyncio.CancelledError):
        await run_due_reports()
    await assert_pending(sessions, schedule_id, due)
    monkeypatch.setattr(reports, 'persist_report', original)
    assert await run_due_reports() == 1
    await assert_one_report(sessions, schedule_id, due)


async def test_competing_schedulers_generate_once(scheduler_db):
    sessions, user_id = scheduler_db
    schedule_id, due = await add_schedule(sessions, user_id)
    completed = await asyncio.gather(run_due_reports(), run_due_reports())
    assert sum(completed) == 1
    await assert_one_report(sessions, schedule_id, due)


async def test_failed_job_does_not_prevent_next_schedule(scheduler_db, monkeypatch):
    sessions, user_id = scheduler_db
    failed_id, due = await add_schedule(sessions, user_id, 'Fail this report')
    await add_schedule(sessions, user_id, 'Keep this report')
    original = reports.persist_report
    async def selective_failure(db, body, user):
        if body.title == 'Fail this report':
            raise RuntimeError('One failed job')
        return await original(db, body, user)
    monkeypatch.setattr(reports, 'persist_report', selective_failure)
    assert await run_due_reports() == 1
    await assert_pending(sessions, failed_id, due)


@pytest.mark.parametrize('reason', ['inactive', 'role_revoked'])
async def test_unauthorized_owner_keeps_occurrence_pending(scheduler_db, reason):
    sessions, user_id = scheduler_db
    schedule_id, due = await add_schedule(sessions, user_id)
    async with sessions() as db:
        user = await db.get(User, user_id)
        if reason == 'inactive':
            user.is_active = False
        else:
            user.role = UserRole.OPERATOR
        await db.commit()
    assert await run_due_reports() == 0
    await assert_pending(sessions, schedule_id, due)


async def test_commit_failure_removes_file_and_allows_retry(scheduler_db, monkeypatch):
    sessions, user_id = scheduler_db
    schedule_id, due = await add_schedule(sessions, user_id)
    original = AsyncSession.commit
    async def fail_commit(self):
        raise RuntimeError('Commit failed before persistence')
    monkeypatch.setattr(AsyncSession, 'commit', fail_commit)
    assert await run_due_reports() == 0
    await assert_pending(sessions, schedule_id, due)
    assert list(Path(settings.REPORTS_DIR).glob('*')) == []
    monkeypatch.setattr(AsyncSession, 'commit', original)
    assert await run_due_reports() == 1
    await assert_one_report(sessions, schedule_id, due)


async def test_refresh_failure_happens_before_commit_and_recovers(scheduler_db, monkeypatch):
    sessions, user_id = scheduler_db
    schedule_id, due = await add_schedule(sessions, user_id)
    original = AsyncSession.refresh
    async def fail_refresh(self, instance, *args, **kwargs):
        if isinstance(instance, Report):
            raise RuntimeError('Refresh failed')
        return await original(self, instance, *args, **kwargs)
    monkeypatch.setattr(AsyncSession, 'refresh', fail_refresh)
    assert await run_due_reports() == 0
    await assert_pending(sessions, schedule_id, due)
    async with sessions() as db:
        assert (await db.execute(select(Report))).scalars().all() == []
    assert list(Path(settings.REPORTS_DIR).glob('*')) == []
    monkeypatch.setattr(AsyncSession, 'refresh', original)
    assert await run_due_reports() == 1
    await assert_one_report(sessions, schedule_id, due)
