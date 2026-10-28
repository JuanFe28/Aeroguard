"""Regresiones de seguridad y persistencia posteriores a la auditoría."""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from pydantic import ValidationError
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core import database
from app.core.config import Settings, settings
from app.core.security import hash_password, verify_password
from app.models.models import Base, AuditLog, ReportSchedule
from app.services.audit_service import log_audit, verify_audit_chain


def login(client, username='admin', password='Admin@12345'):
    response = client.post('/api/v1/auth/token', data={'username': username, 'password': password})
    assert response.status_code == 200, response.text
    return response.json()


def auth(data):
    return {'Authorization': 'Bearer ' + data['access_token']}


def new_user(client):
    administrator = login(client)
    name = 'test_' + uuid.uuid4().hex[:12]
    response = client.post('/api/v1/users', headers=auth(administrator), json={
        'username': name, 'email': name + '@example.org', 'password': 'TestStrong123!',
        'first_name': 'Regression', 'last_name': 'User', 'role': 'operator'})
    assert response.status_code == 201, response.text
    return name, response.json()


def test_logout_revokes_access_and_refresh(isolated_client):
    name, _ = new_user(isolated_client)
    data = login(isolated_client, name, 'TestStrong123!')
    assert isolated_client.post('/api/v1/auth/logout', headers=auth(data)).status_code == 204
    assert isolated_client.get('/api/v1/auth/me', headers=auth(data)).status_code == 401
    assert isolated_client.post('/api/v1/auth/refresh', json={'refresh_token': data['refresh_token']}).status_code == 401
    assert login(isolated_client, name, 'TestStrong123!')['access_token'] != data['access_token']


def test_reset_single_use_and_no_token_logging(isolated_client, monkeypatch, capsys):
    name, user = new_user(isolated_client)
    old = login(isolated_client, name, 'TestStrong123!')
    tokens = []
    async def capture(email, token):
        tokens.append(token)
        return True
    monkeypatch.setattr('app.services.email_service.send_reset_email', capture)
    assert isolated_client.post('/api/v1/auth/request-reset', json={'email': user['email']}).status_code == 202
    assert len(tokens) == 1
    payload = {'token': tokens[0], 'new_password': 'ChangedStrong123!'}
    assert isolated_client.post('/api/v1/auth/reset-password', json=payload).status_code == 204
    assert isolated_client.post('/api/v1/auth/reset-password', json=payload).status_code == 400
    assert isolated_client.get('/api/v1/auth/me', headers=auth(old)).status_code == 401
    login(isolated_client, name, 'ChangedStrong123!')
    assert tokens[0] not in capsys.readouterr().out


def test_bcrypt_never_truncates_utf8():
    password = 'Aa1!' + 'ñ' * 34
    digest = hash_password(password)
    assert verify_password(password, digest)
    assert not verify_password(password + 'x', digest)
    with pytest.raises(ValueError):
        hash_password(password + 'x')


def test_production_rejects_demo_and_default_secret():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APP_ENV='production', DEBUG=False,
                 SECRET_KEY=Settings.model_fields['SECRET_KEY'].default,
                 SEED_DEMO_DATA=False, ALLOW_DEMO_TOKENS=False, ALLOW_SQLITE_FALLBACK=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APP_ENV='production', DEBUG=False, SECRET_KEY='x'*48,
                 SEED_DEMO_DATA=True, ALLOW_DEMO_TOKENS=False, ALLOW_SQLITE_FALLBACK=False)


def test_auth_rate_limit_is_enforced(isolated_client, monkeypatch):
    monkeypatch.setattr(settings, 'AUTH_RATE_LIMIT', 1)
    response = isolated_client.post('/api/v1/auth/token', data={'username': 'missing', 'password': 'wrong'})
    assert response.status_code == 429
    assert int(response.headers['Retry-After']) > 0


def test_real_report_persists_bytes_and_detects_tampering(isolated_client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'REPORTS_DIR', str(tmp_path))
    headers = auth(login(isolated_client))
    response = isolated_client.post('/api/v1/reports', headers=headers, json={'title': 'Regression', 'type': 'detections', 'format': 'csv'})
    assert response.status_code == 201, response.text
    record = response.json()
    path = tmp_path / record['params']['storage_name']
    original = path.read_bytes()
    downloaded = isolated_client.get(record['file_url'], headers=headers)
    assert downloaded.content == original
    assert downloaded.headers['X-AeroGuard-Data-Source'] == 'database'
    path.write_bytes(b'tampered')
    assert isolated_client.get(record['file_url'], headers=headers).status_code == 409
    path.unlink()
    assert isolated_client.get(record['file_url'], headers=headers).status_code == 404


def test_report_dates_and_type_validation(isolated_client):
    headers = auth(login(isolated_client))
    assert isolated_client.get('/api/v1/reports/export/csv?type=invalid', headers=headers).status_code == 422
    assert isolated_client.get('/api/v1/reports/export/pdf?date_from=2030-01-01&date_to=2020-01-01', headers=headers).status_code == 422


def test_configuration_survives_memory_change(isolated_client, monkeypatch):
    headers = auth(login(isolated_client))
    original = isolated_client.get('/api/v1/config', headers=headers).json()
    changed = {**original, 'detection_max_speed': 275}
    assert isolated_client.put('/api/v1/config', json=changed, headers=headers).status_code == 200
    monkeypatch.setattr(settings, 'DETECTION_MAX_SPEED', 1)
    assert isolated_client.get('/api/v1/config', headers=headers).json()['detection_max_speed'] == 275
    assert isolated_client.put('/api/v1/config', json=original, headers=headers).status_code == 200


def test_telemetry_keeps_sensor_and_track(isolated_client, monkeypatch):
    headers = auth(login(isolated_client))
    sensor = isolated_client.post('/api/v1/sensors', headers=headers, json={'name': uuid.uuid4().hex, 'latitude': 7, 'longitude': -73}).json()
    payload = {'sensor_id': sensor['id'], 'object_id': 'object-1', 'latitude': 7, 'longitude': -73, 'altitude': 100, 'speed': 10, 'heading': 0}
    first = isolated_client.post('/api/v1/sensors/telemetry', headers=headers, json=payload)
    second = isolated_client.post('/api/v1/sensors/telemetry', headers=headers, json={**payload, 'latitude': 7.001})
    assert first.status_code == second.status_code == 202, second.text
    assert first.json()['detection_id'] == second.json()['detection_id']
    trajectory = isolated_client.get('/api/v1/detections/' + first.json()['detection_id'] + '/trajectory', headers=headers).json()
    assert [point['sequence'] for point in trajectory] == [0, 1]
    stored = isolated_client.get('/api/v1/sensors/' + sensor['id'], headers=headers).json()
    assert stored['detections_count'] == 1
    monkeypatch.setattr(settings, 'SEED_DEMO_DATA', False)
    assert isolated_client.post('/api/v1/sensors/telemetry', headers=headers, json={**payload, 'sensor_id': 'unknown'}).status_code == 404
    isolated_client.put('/api/v1/sensors/' + sensor['id'], headers=headers, json={'status': 'inactive'})
    assert isolated_client.post('/api/v1/sensors/telemetry', headers=headers, json=payload).status_code == 409


def test_schedule_executes_once(isolated_client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'REPORTS_DIR', str(tmp_path))
    headers = auth(login(isolated_client))
    response = isolated_client.post('/api/v1/reports/schedules', headers=headers, json={'name': 'Regression Schedule', 'format': 'csv', 'cron_expr': '0 0 * * *'})
    assert response.status_code == 201, response.text
    schedule_id = response.json()['id']
    async def run():
        async with database.AsyncSessionLocal() as db:
            schedule = await db.get(ReportSchedule, schedule_id)
            schedule.next_run = datetime.now(timezone.utc) - timedelta(minutes=1)
            await db.commit()
        from app.services.report_scheduler_service import run_due_reports
        assert await run_due_reports() == 1
        assert await run_due_reports() == 0
    isolated_client.portal.call(run)
    assert len(list(tmp_path.glob('*.csv'))) == 1
    assert isolated_client.delete('/api/v1/reports/schedules/' + schedule_id, headers=headers).status_code == 204


@pytest.mark.asyncio
async def test_audit_detects_tail_deletion_and_partial_checks():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            await log_audit(db, 'A', 'test', 'tester')
            last = await log_audit(db, 'B', 'test', 'tester')
            assert (await verify_audit_chain(db, limit=1))['valid'] is None
            await db.delete(last)
            await db.commit()
            assert (await verify_audit_chain(db))['valid'] is False
    finally:
        await engine.dispose()


def test_monitoring_requires_authentication(isolated_client):
    assert isolated_client.get('/ready').status_code == 200
    assert isolated_client.get('/metrics').status_code == 401
    result = isolated_client.get('/metrics', headers=auth(login(isolated_client)))
    assert result.status_code == 200
    assert b'aeroguard_http_requests_total' in result.content


def test_metrics_token_cannot_access_operational_api(isolated_client, monkeypatch):
    token = 'metrics-only-' + uuid.uuid4().hex
    monkeypatch.setattr(settings, 'METRICS_BEARER_TOKEN', token)
    headers = {'Authorization': 'Bearer ' + token}
    assert isolated_client.get('/metrics', headers=headers).status_code == 200
    assert isolated_client.get('/api/v1/users', headers=headers).status_code == 401


def test_websocket_credentials_are_redacted_from_logs():
    import logging
    from app.core.logging_security import RedactCredentials
    record = logging.LogRecord('uvicorn.error', logging.INFO, '', 0, 'WebSocket %s', ('/ws/live?token=private-secret',), None)
    assert RedactCredentials().filter(record)
    assert 'private-secret' not in record.getMessage()


def test_worker_result_is_idempotent_and_identifies_experiment(isolated_client):
    headers = auth(login(isolated_client))
    created = isolated_client.post('/api/v1/detections', headers=headers, json={'latitude': 7, 'longitude': -73, 'altitude': 100, 'speed': 10, 'heading': 1})
    assert created.status_code == 201, created.text
    path = '/api/v1/detections/' + created.json()['id'] + '/ai-analysis'
    body = {'job_id': 'test-job', 'is_drone': False, 'confidence': 0.1, 'model_used': 'OpenCV-Heuristic', 'processing_ms': 5}
    first = isolated_client.post(path, headers=headers, json=body)
    second = isolated_client.post(path, headers=headers, json={**body, 'confidence': 0.8})
    assert first.status_code == second.status_code == 200
    assert first.json()['event_id'] == second.json()['event_id']
    stored = isolated_client.get(path, headers=headers).json()
    assert stored['confidence'] == 0.1
    assert stored['model_validated'] is False

