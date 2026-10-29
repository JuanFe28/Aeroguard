"""
AeroGuard — Alerts Endpoint (RF-013 a RF-016)
Gestión del ciclo de vida de alertas: emisión, asignación, resolución y notificación.
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.models import Alert, AlertStatus, AlertSeverity, AlertType
from app.services.audit_service import log_audit

router = APIRouter()
logger = structlog.get_logger("AeroGuard-Alerts")


class AlertCreateSchema(BaseModel):
    detection_id: Optional[str] = None
    type: AlertType = AlertType.RESTRICTED_ZONE
    severity: AlertSeverity = AlertSeverity.HIGH
    title: str
    message: str


class AlertResolveSchema(BaseModel):
    notes: str


@router.get("", summary="Listar alertas (RF-013)")
async def list_alerts(
    status: Optional[AlertStatus] = None,
    severity: Optional[AlertSeverity] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("alerts:read")),
):
    """Lista alertas del sistema ordenadas cronológicamente inverso."""
    query = select(Alert).order_by(desc(Alert.created_at)).offset(skip).limit(limit)
    if status:
        query = query.where(Alert.status == status)
    if severity:
        query = query.where(Alert.severity == severity)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("", status_code=status.HTTP_201_CREATED, summary="Generar alerta (RF-013)")
async def create_alert(
    body: AlertCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("alerts:write")),
):
    """Crea una nueva alerta de seguridad."""
    alert = Alert(
        detection_id=body.detection_id,
        type=body.type,
        severity=body.severity,
        status=AlertStatus.OPEN,
        title=body.title,
        message=body.message,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.patch("/{alert_id}/assign", summary="Asignar alerta a operador (RF-015)")
async def assign_alert(
    alert_id: str,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("alerts:write")),
):
    """Asigna la alerta al operador especificado o al usuario actual si no se provee ID."""
    query = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada.")

    assigned_target = user_id or str(getattr(current_user, "id", ""))
    setattr(alert, "assigned_to_id", assigned_target)
    setattr(alert, "status", AlertStatus.ASSIGNED)

    await log_audit(
        db=db,
        action="ALERT_ASSIGNED",
        resource="alert",
        resource_id=alert_id,
        username=current_user.username,
        user_id=current_user.id,
        details={"assigned_to": assigned_target},
    )

    await db.commit()
    await db.refresh(alert)
    return alert


@router.patch("/{alert_id}/resolve", summary="Resolver alerta con justificación (RF-015)")
async def resolve_alert(
    alert_id: str,
    body: AlertResolveSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("alerts:write")),
):
    """Marca la alerta como resuelta e incluye notas de resolución obligatorias."""
    query = select(Alert).where(Alert.id == alert_id)
    result = await db.execute(query)
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada.")

    setattr(alert, "status", AlertStatus.RESOLVED)
    setattr(alert, "resolved_at", datetime.now(timezone.utc))
    setattr(alert, "resolved_by_id", str(getattr(current_user, "id", "")))
    setattr(alert, "notes", body.notes)

    await log_audit(
        db=db,
        action="ALERT_RESOLVED",
        resource="alert",
        resource_id=alert_id,
        username=current_user.username,
        user_id=current_user.id,
        details={"notes": body.notes},
    )

    await db.commit()
    await db.refresh(alert)
    return alert


# ============================================================
# Dictamen Táctico de IA (SOAR / n8n / Agente C-UAS)
# ============================================================

class AIVerdictSchema(BaseModel):
    incident_id: str
    ai_verdict: str
    drone_id: Optional[str] = None
    threat_level: Optional[str] = None


_latest_verdict: dict = {
    "incident_id": None,
    "timestamp": None,
    "ai_verdict": "Sin dictámenes registrados.",
    "threat_level": None,
    "drone_id": None
}


@router.get("/ai-verdict", summary="Consultar último dictamen táctico de IA")
async def get_latest_ai_verdict(current_user = Depends(require_permission("alerts:read"))):
    """Retorna el dictamen táctico más reciente emitido por el agente IA / SOAR."""
    return _latest_verdict


@router.post("/ai-verdict", summary="Registrar dictamen táctico de IA (n8n / Agente)")
async def register_ai_verdict(
    body: AIVerdictSchema,
    current_user = Depends(require_permission("alerts:write")),
):
    """Callback invocado por el workflow n8n o agente autónomo C-UAS."""
    global _latest_verdict
    _latest_verdict = {
        "incident_id": body.incident_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ai_verdict": body.ai_verdict,
        "threat_level": body.threat_level,
        "drone_id": body.drone_id
    }

    try:
        from app.api.v1.endpoints.websocket import manager
        await manager.broadcast({
            "type": "ai_verdict",
            "data": _latest_verdict
        })
    except Exception as error:
        logger.warning("No se pudo retransmitir el dictamen por WebSocket", error=str(error))

    return {"status": "success", "message": "Dictamen registrado", "data": _latest_verdict}


class DroneTelemetrySchema(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    drone_id: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_m: float = Field(ge=0, le=15000)
    speed_ms: float = Field(ge=0)
    heading_deg: float = Field(ge=0, le=360)
    ai_confidence: Optional[float] = Field(default=None, ge=0, le=1)


class ZoneInfoSchema(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    name: str = Field(min_length=1)
    max_allowed_altitude_m: float = Field(ge=0, le=15000)
    restriction_type: Optional[str] = "NO_FLY_ZONE"


class TriggerIncidentSchema(BaseModel):
    event_type: Optional[str] = "TELEMETRY_REVIEW"
    incident_id: Optional[str] = None
    drone: DroneTelemetrySchema
    zone: ZoneInfoSchema


@router.post("/trigger-incident", summary="Disparar análisis de incidente táctico hacia n8n / Agente IA")
async def trigger_tactical_incident(
    body: TriggerIncidentSchema,
    current_user = Depends(require_permission("alerts:write")),
):
    """
    Dispara el análisis táctico de un incidente aéreo:
    - Despacha webhook hacia n8n SOAR
    - Ejecuta motor táctico embebido si n8n no está disponible
    - Retransmite el dictamen generado en tiempo real por WebSocket
    """
    from app.services.ai_tactical_agent_service import ai_tactical_service

    payload = {
        "event_type": body.event_type or "TELEMETRY_REVIEW",
        "incident_id": body.incident_id or f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "drone": body.drone.model_dump(),
        "zone": body.zone.model_dump()
    }

    result = await ai_tactical_service.analyze_incident(payload)
    return {
        "status": "success",
        "message": "Incidente analizado táctica y operativamente",
        "data": result
    }

