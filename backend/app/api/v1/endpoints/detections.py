"""
AeroGuard — Detections Endpoint (RF-005 a RF-012)
Gestión, consulta y actualización de detecciones de drones.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.models import Detection, DetectionStatus, ThreatLevel, TrajectoryPoint, Alert, AlertStatus, AlertType, AlertSeverity

router = APIRouter()


class AIAnalysisSchema(BaseModel):
    job_id: str = Field(min_length=1, max_length=128)
    is_drone: bool
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    model_used: str = Field(min_length=1, max_length=128)
    processing_ms: float = Field(ge=0, allow_inf_nan=False)


@router.post('/{detection_id}/ai-analysis')
async def save_ai_analysis(detection_id: str, body: AIAnalysisSchema, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('detections:write'))):
    from app.models.models import Event
    from uuid import UUID, uuid5, NAMESPACE_URL
    try:
        detection_id = str(UUID(detection_id))
    except ValueError:
        raise HTTPException(422, 'Identificador inválido.')
    detection = await db.get(Detection, detection_id)
    if detection is None:
        raise HTTPException(404, 'Detección no encontrada.')
    event_id = str(uuid5(NAMESPACE_URL, detection_id + ':' + body.job_id))
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert = pg_insert if db.bind.dialect.name == 'postgresql' else sqlite_insert
    statement = insert(Event).values(id=event_id, detection_id=detection_id, event_type='ai_analysis',
        data={**body.model_dump(), 'model_validated': False, 'confidence_kind': 'uncalibrated_score'}).on_conflict_do_nothing().returning(Event.id)
    if (await db.execute(statement)).scalar_one_or_none() is not None:
        detection.ai_analyzed = True
        detection.ai_confidence = body.confidence
        detection.is_drone = body.is_drone
    await db.commit()
    return {'status': 'stored', 'event_id': event_id, 'model_validated': False}


@router.get('/{detection_id}/ai-analysis')
async def get_ai_analysis(detection_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('detections:read'))):
    from app.models.models import Event
    event = (await db.execute(select(Event).where(Event.detection_id == detection_id, Event.event_type == 'ai_analysis').order_by(Event.timestamp.desc()).limit(1))).scalar_one_or_none()
    if event is None:
        raise HTTPException(404, 'Sin análisis visual asociado.')
    return event.data


class DetectionCreateSchema(BaseModel):
    sensor_id: Optional[str] = None
    latitude: float
    longitude: float
    altitude: float
    speed: float
    heading: float
    threat_level: ThreatLevel = ThreatLevel.LOW
    ai_analyzed: bool = False
    ai_confidence: Optional[float] = None
    is_drone: bool = False
    image_url: Optional[str] = None
    zone_id: Optional[str] = None
    notes: Optional[str] = None


@router.get("", summary="Listar detecciones con filtros (RF-009)")
async def list_detections(
    status: Optional[DetectionStatus] = None,
    threat_level: Optional[ThreatLevel] = None,
    is_drone: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("detections:read")),
):
    """Lista detecciones ordenadas por fecha más reciente."""
    query = select(Detection).order_by(desc(Detection.created_at)).offset(skip).limit(limit)
    if status:
        query = query.where(Detection.status == status)
    if threat_level:
        query = query.where(Detection.threat_level == threat_level)
    if is_drone is not None:
        query = query.where(Detection.is_drone == is_drone)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/active", summary="Obtener detecciones activas en tiempo real (RF-005)")
async def get_active_detections(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("detections:read")),
):
    """Retorna únicamente las detecciones activas para el mapa del Dashboard."""
    query = select(Detection).where(Detection.status == DetectionStatus.ACTIVE).order_by(desc(Detection.created_at))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{detection_id}", summary="Detalle de detección")
async def get_detection(
    detection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("detections:read")),
):
    """Obtiene el detalle completo de una detección."""
    query = select(Detection).where(Detection.id == detection_id)
    result = await db.execute(query)
    detection = result.scalar_one_or_none()
    if not detection:
        raise HTTPException(status_code=404, detail="Detección no encontrada.")
    return detection


@router.post("", status_code=status.HTTP_201_CREATED, summary="Registrar nueva detección (RF-005)")
async def create_detection(
    body: DetectionCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("detections:write")),
):
    """Crea un nuevo registro de detección y su primer punto de trayectoria."""
    detection = Detection(
        sensor_id=body.sensor_id,
        latitude=body.latitude,
        longitude=body.longitude,
        altitude=body.altitude,
        speed=body.speed,
        heading=body.heading,
        status=DetectionStatus.ACTIVE,
        threat_level=body.threat_level,
        ai_analyzed=body.ai_analyzed,
        ai_confidence=body.ai_confidence,
        is_drone=body.is_drone,
        image_url=body.image_url,
        zone_id=body.zone_id,
        notes=body.notes,
    )
    db.add(detection)
    await db.flush()

    # Agregar punto de trayectoria inicial
    trajectory_pt = TrajectoryPoint(
        detection_id=detection.id,
        latitude=body.latitude,
        longitude=body.longitude,
        altitude=body.altitude,
        speed=body.speed,
        heading=body.heading,
    )
    db.add(trajectory_pt)
    await db.commit()
    await db.refresh(detection)
    
    # RF-012 Geofencing Trigger Automático
    if body.zone_id:
        alert = Alert(
            detection_id=detection.id,
            type=AlertType.RESTRICTED_ZONE,
            severity=AlertSeverity.HIGH if body.threat_level == ThreatLevel.HIGH else AlertSeverity.MEDIUM,
            status=AlertStatus.OPEN,
            title="Incursión en Zona Restringida",
            message=f"El dron ha incursionado automáticamente en la zona restringida: {body.zone_id}."
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

    return detection


@router.patch("/{detection_id}/status", summary="Actualizar estado de detección")
async def update_detection_status(
    detection_id: str,
    new_status: DetectionStatus,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("detections:write")),
):
    """Cambia el estado de una detección (active, pending, resolved, discarded)."""
    query = select(Detection).where(Detection.id == detection_id)
    result = await db.execute(query)
    detection = result.scalar_one_or_none()
    if not detection:
        raise HTTPException(status_code=404, detail="Detección no encontrada.")

    detection.status = new_status
    await db.commit()
    await db.refresh(detection)
    return detection


@router.get("/{detection_id}/trajectory", summary="Consultar trayectoria histórica (RF-011)")
async def get_trajectory(
    detection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("detections:read")),
):
    """Retorna los puntos de trayectoria para reconstrucción de vuelo en 2D/3D."""
    from uuid import UUID
    try:
        detection_id = str(UUID(detection_id))
    except ValueError:
        raise HTTPException(422, 'Identificador inválido.')
    if await db.get(Detection, detection_id) is None:
        raise HTTPException(404, 'Detección no encontrada.')
    query = select(TrajectoryPoint).where(TrajectoryPoint.detection_id == detection_id).order_by(TrajectoryPoint.timestamp.asc(), TrajectoryPoint.sequence.asc(), TrajectoryPoint.id.asc())
    result = await db.execute(query)
    return result.scalars().all()
