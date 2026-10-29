from app.core.validation import valid_uuid
"""Reportes de BD, archivos recuperables por ID y programación UTC."""
import csv
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import uuid
from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.core.database import get_db
from app.core.security import require_permission
from app.models.models import Report, ReportType, ReportFormat, ReportSchedule
from app.services.report_data_service import build_dataset, utc
from app.services.report_generator_service import report_generator_service

router = APIRouter()
MEDIA = {'pdf': 'application/pdf', 'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'csv': 'text/csv; charset=utf-8'}
EXT = {'pdf': 'pdf', 'excel': 'xlsx', 'csv': 'csv'}

class ReportCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    type: ReportType = ReportType.SUMMARY
    format: ReportFormat = ReportFormat.PDF
    date_from: datetime | None = None
    date_to: datetime | None = None
    params: dict = Field(default_factory=dict)
    @model_validator(mode='after')
    def dates(self):
        if self.date_from and self.date_to and utc(self.date_from) > utc(self.date_to):
            raise ValueError('Rango de fechas inválido.')
        return self

class ReportExportRequestSchema(BaseModel):
    format: ReportFormat = ReportFormat.PDF
    type: ReportType = ReportType.DETECTIONS
    date_from: datetime | None = None
    date_to: datetime | None = None

def safe_cell(value):
    return "'" + value if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r')) else value

def compile_report(data, fmt):
    if fmt == ReportFormat.PDF:
        return report_generator_service.generate_pdf(data=data)
    if fmt == ReportFormat.EXCEL:
        return report_generator_service.generate_excel(data=data)
    buffer = io.StringIO(newline='')
    rows = data['audit_records'] if data['report_type'] == 'audit' else data['incursions']
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]) if rows else ['id', 'timestamp'])
    writer.writeheader()
    for row in rows:
        writer.writerow({key: safe_cell(value) for key, value in row.items()})
    result = buffer.getvalue().encode('utf-8-sig')
    return result, hashlib.sha256(result).hexdigest()

def download(content, fmt, filename, data_hash):
    return Response(content=content, media_type=MEDIA[fmt], headers={
        'Content-Disposition': f'attachment; filename="{filename}"', 'X-Report-SHA256': data_hash,
        'X-Content-SHA256': hashlib.sha256(content).hexdigest(), 'X-AeroGuard-Data-Source': 'database'})

async def export(db, user, fmt, type, date_from=None, date_to=None):
    try:
        data = await build_dataset(db, type, date_from, date_to, user.username)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    content, digest = await run_in_threadpool(compile_report, data, fmt)
    return download(content, fmt.value, f'aeroguard_{uuid.uuid4().hex}.{EXT[fmt]}', digest)

@router.get('/export/pdf')
async def export_pdf_report(type: ReportType = ReportType.DETECTIONS, date_from: datetime | None = None, date_to: datetime | None = None,
                            db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:read'))):
    return await export(db, current_user, ReportFormat.PDF, type, date_from, date_to)

@router.get('/export/excel')
async def export_excel_report(type: ReportType = ReportType.DETECTIONS, date_from: datetime | None = None, date_to: datetime | None = None,
                              db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:read'))):
    return await export(db, current_user, ReportFormat.EXCEL, type, date_from, date_to)

@router.get('/export/csv')
async def export_csv_report(type: ReportType = ReportType.DETECTIONS, date_from: datetime | None = None, date_to: datetime | None = None,
                            db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:read'))):
    return await export(db, current_user, ReportFormat.CSV, type, date_from, date_to)

@router.post('/export')
async def export_report_post(body: ReportExportRequestSchema, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:read'))):
    return await export(db, current_user, body.format, body.type, body.date_from, body.date_to)

@router.get('')
async def list_reports(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500), db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:read'))):
    return (await db.execute(select(Report).order_by(Report.created_at.desc()).offset(skip).limit(limit))).scalars().all()

async def persist_report(db, body, current_user):
    data = await build_dataset(db, body.type, body.date_from, body.date_to, current_user.username)
    content, digest = await run_in_threadpool(compile_report, data, body.format)
    report_id = str(uuid.uuid4())
    filename = f'{report_id}.{EXT[body.format]}'
    directory = Path(settings.REPORTS_DIR)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = directory / filename
    try:
        with destination.open('xb') as stream:
            stream.write(content)
        report = Report(id=report_id, title=body.title, type=body.type, format=body.format, date_from=body.date_from,
                        date_to=body.date_to, created_by_id=current_user.id, params={**body.params, 'storage_name': filename,
                        'sha256': digest, 'file_sha256': hashlib.sha256(content).hexdigest(), 'data_source': 'database'},
                        status='completed', file_url=f'/api/v1/reports/{report_id}/download', file_size=len(content),
                        completed_at=datetime.now(timezone.utc))
        db.add(report)
        await db.flush()
        await db.refresh(report)
        # Incluye el avance del cron si el llamador es el scheduler.
        # No ejecutar consultas que puedan fallar después del commit y borrar el archivo.
        await db.commit()
        return report
    except Exception:
        await db.rollback()
        if destination.is_file():
            destination.unlink()
        raise

@router.post('', status_code=201)
async def create_report(body: ReportCreateSchema, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:write'))):
    return await persist_report(db, body, current_user)

class ScheduleSchema(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    report_type: ReportType = ReportType.DETECTIONS
    format: ReportFormat = ReportFormat.PDF
    cron_expr: str
    is_active: bool = True
    @model_validator(mode='after')
    def valid_cron(self):
        CronTrigger.from_crontab(self.cron_expr, timezone='UTC')
        return self

@router.get('/schedules')
async def schedules(db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:read'))):
    return (await db.execute(select(ReportSchedule).order_by(ReportSchedule.created_at))).scalars().all()

@router.post('/schedules', status_code=201)
async def create_schedule(body: ScheduleSchema, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:write'))):
    item = ReportSchedule(**body.model_dump(), created_by=current_user.id, next_run=CronTrigger.from_crontab(body.cron_expr, timezone='UTC').get_next_fire_time(None, datetime.now(timezone.utc)))
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.put('/schedules/{schedule_id}')
async def update_schedule(schedule_id: str, body: ScheduleSchema, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:write'))):
    item = await db.get(ReportSchedule, valid_uuid(schedule_id))
    if item is None:
        raise HTTPException(404, 'Programación no encontrada.')
    for name, value in body.model_dump().items():
        setattr(item, name, value)
    item.next_run = CronTrigger.from_crontab(body.cron_expr, timezone='UTC').get_next_fire_time(None, datetime.now(timezone.utc))
    await db.commit()
    return item

@router.delete('/schedules/{schedule_id}', status_code=204)
async def delete_schedule(schedule_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:write'))):
    item = await db.get(ReportSchedule, valid_uuid(schedule_id))
    if item is None:
        raise HTTPException(404, 'Programación no encontrada.')
    await db.delete(item)
    await db.commit()

async def lookup(db, report_id):
    try:
        uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(404, 'Reporte no encontrado.')
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, 'Reporte no encontrado.')
    return report

@router.get('/{report_id}/download')
async def download_report_by_id(report_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:read'))):
    report = await lookup(db, report_id)
    filename = (report.params or {}).get('storage_name', '')
    if filename != f'{report.id}.{EXT[report.format]}':
        raise HTTPException(409, 'Reporte histórico sin archivo verificable; debe regenerarse.')
    path = Path(settings.REPORTS_DIR) / filename
    if path.is_symlink() or not path.is_file():
        raise HTTPException(404, 'Archivo no disponible.')
    content = await run_in_threadpool(path.read_bytes)
    if hashlib.sha256(content).hexdigest() != report.params.get('file_sha256'):
        raise HTTPException(409, 'La integridad del archivo no coincide.')
    return download(content, report.format.value, filename, report.params['sha256'])

@router.get('/{report_id}')
async def get_report(report_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('reports:read'))):
    return await lookup(db, report_id)
