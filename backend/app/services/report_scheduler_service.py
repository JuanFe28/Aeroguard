"""El reporte y el avance del cron se confirman en una misma transacción."""
import asyncio
from datetime import datetime, timezone
import logging
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update
from app.models.models import ReportSchedule, User

logger = logging.getLogger(__name__)

async def run_due_reports():
    from app.core import database
    from app.api.v1.endpoints.reports import ReportCreateSchema, persist_report
    now = datetime.now(timezone.utc)
    completed = 0
    async with database.AsyncSessionLocal() as db:
        # Copias de valores: rollback expira objetos ORM y no debe impedir procesar
        # las otras programaciones del lote después de un error o permiso revocado.
        due = (await db.execute(select(
            ReportSchedule.id, ReportSchedule.next_run, ReportSchedule.cron_expr,
            ReportSchedule.created_by, ReportSchedule.name, ReportSchedule.report_type,
            ReportSchedule.format,
        ).where(ReportSchedule.is_active.is_(True), ReportSchedule.next_run <= now))).all()
        for item in due:
            next_run = CronTrigger.from_crontab(item.cron_expr, timezone='UTC').get_next_fire_time(None, now)
            claim = await db.execute(update(ReportSchedule).where(ReportSchedule.id == item.id, ReportSchedule.is_active.is_(True), ReportSchedule.next_run == item.next_run).values(
                next_run=next_run, last_run=now).returning(ReportSchedule.id))
            claimed = claim.scalar_one_or_none()
            # Conservar el bloqueo y los cambios sin confirmar hasta persist_report.
            # Una caída o rollback deja la ocurrencia vencida para reintentar.
            if claimed is None:
                await db.rollback()
                continue
            user = await db.get(User, item.created_by, populate_existing=True)
            if user is None or not user.is_active:
                logger.warning('Programación omitida: usuario no disponible', extra={'schedule_id': item.id})
                await db.rollback()
                continue
            from app.core.security import has_permission
            if not has_permission(user.role, 'reports:write'):
                await db.rollback()
                continue
            try:
                await persist_report(db, ReportCreateSchema(title=item.name, type=item.report_type, format=item.format), user)
                completed += 1
            except Exception:
                await db.rollback()
                logger.exception('Falló el reporte programado', extra={'schedule_id': item.id})
    return completed

async def scheduler_loop():
    while True:
        try:
            await run_due_reports()
        except Exception:
            logger.exception('Falló la consulta de reportes programados')
        await asyncio.sleep(5)
