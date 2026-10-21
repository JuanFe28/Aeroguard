"""
AeroGuard — Configuration Endpoint (RF-028)
Consulta y ajuste en caliente de parámetros de detección y umbrales de alerta.
"""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from app.core.database import get_db

from app.core.config import settings
from app.core.security import get_current_user, require_permission

router = APIRouter()


class SystemConfigSchema(BaseModel):
    detection_max_altitude: float = Field(ge=0, le=15000)
    detection_min_speed: float = Field(ge=0, le=1000)
    detection_max_speed: float = Field(ge=0, le=1000)
    ai_confidence_threshold: float = Field(ge=0, le=1)
    ai_enabled: bool
    anomaly_threshold: float = Field(gt=0)
    alerts_enabled: bool

    @model_validator(mode='after')
    def valid_speed(self):
        if self.detection_min_speed > self.detection_max_speed:
            raise ValueError('Rango de velocidad inválido.')
        return self


async def load_persisted_config(db):
    from app.models.models import SystemConfig
    stored = (await db.execute(select(SystemConfig).where(SystemConfig.key == 'operational'))).scalar_one_or_none()
    if stored:
        values = SystemConfigSchema.model_validate(stored.value)
        for key, value in values.model_dump().items():
            setattr(settings, key.upper(), value)


@router.get("", summary="Obtener configuración del sistema (RF-028)")
async def get_system_config(
    db=Depends(get_db),
    current_user = Depends(require_permission("config:read")),
):
    """Devuelve los parámetros operativos actuales del sistema de detección."""
    await load_persisted_config(db)
    return {
        "detection_max_altitude": settings.DETECTION_MAX_ALTITUDE,
        "detection_min_speed": settings.DETECTION_MIN_SPEED,
        "detection_max_speed": settings.DETECTION_MAX_SPEED,
        "ai_confidence_threshold": settings.AI_CONFIDENCE_THRESHOLD,
        "ai_enabled": settings.AI_ENABLED,
        "anomaly_threshold": settings.ANOMALY_THRESHOLD,
        "alerts_enabled": settings.ALERTS_ENABLED,
    }


@router.put("", summary="Actualizar parámetros operativos (RF-028)")
async def update_system_config(
    body: SystemConfigSchema,
    db=Depends(get_db),
    current_user = Depends(require_permission("config:write")),
):
    """Ajusta en tiempo real los umbrales de detección y confianza de IA."""
    from app.models.models import SystemConfig
    stored = (await db.execute(select(SystemConfig).where(SystemConfig.key == 'operational'))).scalar_one_or_none()
    if stored is None:
        stored = SystemConfig(key='operational', value=body.model_dump())
        db.add(stored)
    stored.value = body.model_dump()
    stored.updated_by = current_user.id if not str(current_user.id).startswith('user-') else None
    await db.commit()
    settings.DETECTION_MAX_ALTITUDE = body.detection_max_altitude
    settings.DETECTION_MIN_SPEED = body.detection_min_speed
    settings.DETECTION_MAX_SPEED = body.detection_max_speed
    settings.AI_CONFIDENCE_THRESHOLD = body.ai_confidence_threshold
    settings.AI_ENABLED = body.ai_enabled
    settings.ANOMALY_THRESHOLD = body.anomaly_threshold
    settings.ALERTS_ENABLED = body.alerts_enabled

    return {
        "status": "updated",
        "config": {
            "detection_max_altitude": settings.DETECTION_MAX_ALTITUDE,
            "detection_min_speed": settings.DETECTION_MIN_SPEED,
            "detection_max_speed": settings.DETECTION_MAX_SPEED,
            "ai_confidence_threshold": settings.AI_CONFIDENCE_THRESHOLD,
            "ai_enabled": settings.AI_ENABLED,
            "anomaly_threshold": settings.ANOMALY_THRESHOLD,
            "alerts_enabled": settings.ALERTS_ENABLED,
        }
    }
