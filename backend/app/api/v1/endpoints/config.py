"""
AeroGuard — Configuration Endpoint (RF-028)
Consulta y ajuste en caliente de parámetros de detección y umbrales de alerta.
"""

from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import get_current_user, require_permission

router = APIRouter()


class SystemConfigSchema(BaseModel):
    detection_max_altitude: float
    detection_min_speed: float
    detection_max_speed: float
    ai_confidence_threshold: float
    ai_enabled: bool
    anomaly_threshold: float
    alerts_enabled: bool


@router.get("", summary="Obtener configuración del sistema (RF-028)")
async def get_system_config(
    current_user = Depends(require_permission("config:read")),
):
    """Devuelve los parámetros operativos actuales del sistema de detección."""
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
    current_user = Depends(require_permission("config:write")),
):
    """Ajusta en tiempo real los umbrales de detección y confianza de IA."""
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
