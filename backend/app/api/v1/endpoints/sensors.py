"""
AeroGuard — Sensors Endpoint (RF-020 a RF-023)
Gestión, configuración y monitoreo del estado de sensores físicos o simulados.
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.models import Sensor, SensorType, SensorStatus

router = APIRouter()


class SensorCreateSchema(BaseModel):
    name: str
    type: SensorType = SensorType.RADAR
    status: SensorStatus = SensorStatus.ACTIVE
    latitude: float
    longitude: float
    altitude: float = 0.0
    range_km: float = 5.0
    config: dict = {}


class SensorUpdateSchema(BaseModel):
    name: Optional[str] = None
    type: Optional[SensorType] = None
    status: Optional[SensorStatus] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    range_km: Optional[float] = None
    config: Optional[dict] = None


@router.get("", summary="Listar todos los sensores (RF-020)")
async def list_sensors(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("sensors:read")),
):
    """Lista todos los sensores registrados con su estado y estadísticas."""
    query = select(Sensor).order_by(Sensor.name.asc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", status_code=status.HTTP_201_CREATED, summary="Registrar nuevo sensor (RF-021)")
async def create_sensor(
    body: SensorCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("sensors:write")),
):
    """Registra un nuevo sensor en la red de defensa."""
    sensor = Sensor(
        name=body.name,
        type=body.type,
        status=body.status,
        latitude=body.latitude,
        longitude=body.longitude,
        altitude=body.altitude,
        range_km=body.range_km,
        config=body.config,
        last_active=datetime.now(timezone.utc),
    )
    db.add(sensor)
    await db.commit()
    await db.refresh(sensor)
    return sensor


@router.get("/{sensor_id}", summary="Detalle de sensor")
async def get_sensor(
    sensor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("sensors:read")),
):
    """Obtiene el detalle de un sensor por ID."""
    query = select(Sensor).where(Sensor.id == sensor_id)
    result = await db.execute(query)
    sensor = result.scalar_one_or_none()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor no encontrado.")
    return sensor


@router.put("/{sensor_id}", summary="Actualizar sensor")
async def update_sensor(
    sensor_id: str,
    body: SensorUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("sensors:write")),
):
    """Actualiza configuración y parámetros del sensor."""
    query = select(Sensor).where(Sensor.id == sensor_id)
    result = await db.execute(query)
    sensor = result.scalar_one_or_none()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor no encontrado.")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(sensor, field, val)

    await db.commit()
    await db.refresh(sensor)
    return sensor


@router.delete("/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar sensor")
async def delete_sensor(
    sensor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("sensors:write")),
):
    """Elimina un sensor de la red."""
    query = select(Sensor).where(Sensor.id == sensor_id)
    result = await db.execute(query)
    sensor = result.scalar_one_or_none()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor no encontrado.")

    await db.delete(sensor)
    await db.commit()


# ============================================================
# Telemetry Ingest (RF-020, RF-012, RF-013)
# ============================================================

class TelemetryPacketSchema(BaseModel):
    sensor_id: str
    latitude: float
    longitude: float
    altitude: float
    speed: float
    heading: float
    timestamp: Optional[str] = None
    signal_strength: Optional[float] = None


@router.post("/telemetry", status_code=status.HTTP_202_ACCEPTED, summary="Ingesta de telemetría de sensores (RF-020)")
async def ingest_telemetry(
    packet: TelemetryPacketSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("detections:write")),
):
    """
    Procesa telemetría proveniente de sensores físicos o simuladores.
    - Valida rangos para descartar ruido o lecturas inválidas (RF-029).
    - Crea o actualiza detección activa con punto de trayectoria.
    - Evalúa proximidad a zonas restringidas para disparo de alertas (RF-012).
    - Emite evento en tiempo real vía WebSockets.
    """
    # 1. Validación de rangos (ruido / datos corruptos)
    if not (-90.0 <= packet.latitude <= 90.0) or not (-180.0 <= packet.longitude <= 180.0):
        raise HTTPException(status_code=400, detail="Coordenadas geográficas fuera de rango.")
    if packet.altitude < 0 or packet.altitude > 10000 or packet.speed < 0 or packet.speed > 1000:
        raise HTTPException(status_code=400, detail="Parámetros cinemáticos fuera de rango operacional.")

    from app.models.models import Detection, TrajectoryPoint, Alert, RestrictedZone, DetectionStatus, ThreatLevel, AlertSeverity, AlertType
    from app.api.v1.endpoints.websocket import broadcast_detection, broadcast_alert
    from app.services.geospatial_service import geospatial_service

    # 2. Registrar o asociar detección
    detection = Detection(
        latitude=packet.latitude,
        longitude=packet.longitude,
        altitude=packet.altitude,
        speed=packet.speed,
        heading=packet.heading,
        status=DetectionStatus.ACTIVE,
        threat_level=ThreatLevel.MEDIUM if packet.altitude < 300 else ThreatLevel.LOW,
        is_drone=False,
        ai_analyzed=False,
        ai_confidence=None,
    )
    db.add(detection)
    await db.flush()

    # 3. Guardar punto de trayectoria
    point = TrajectoryPoint(
        detection_id=detection.id,
        latitude=packet.latitude,
        longitude=packet.longitude,
        altitude=packet.altitude,
        speed=packet.speed,
        heading=packet.heading,
    )
    db.add(point)

    # 4. Verificar invasión de zona restringida (RF-012) usando GeospatialService (PostGIS / Ray-Casting)
    zones_query = select(RestrictedZone).where(RestrictedZone.is_active == True)
    zones_res = await db.execute(zones_query)
    zones = zones_res.scalars().all()

    alert_created = None
    active_breaches, highest_breach = geospatial_service.evaluate_all_zones(
        packet.latitude,
        packet.longitude,
        packet.altitude,
        zones,
    )

    if highest_breach:
        detection.zone_id = highest_breach["zone_id"]
        threat_str = highest_breach["threat_level"].lower()
        severity_map = {
            "critical": AlertSeverity.CRITICAL,
            "high": AlertSeverity.HIGH,
            "medium": AlertSeverity.MEDIUM,
            "low": AlertSeverity.LOW,
        }
        severity_enum = severity_map.get(threat_str, AlertSeverity.HIGH)
        threat_enum_map = {
            "critical": ThreatLevel.CRITICAL,
            "high": ThreatLevel.HIGH,
            "medium": ThreatLevel.MEDIUM,
            "low": ThreatLevel.LOW,
        }
        if threat_str in threat_enum_map:
            detection.threat_level = threat_enum_map[threat_str]

        alert = Alert(
            detection_id=detection.id,
            type=AlertType.RESTRICTED_ZONE,
            severity=severity_enum,
            title=f"Invasión de Zona Restringida: {highest_breach['zone_name']}",
            message=(
                f"Aeronave a {packet.altitude:.0f}m detectada dentro del polígono geoespacial protegido "
                f"'{highest_breach['zone_name']}' a {packet.speed:.0f} km/h (Techo permitido: {highest_breach['max_altitude']:.0f}m)."
            ),
        )
        db.add(alert)
        await db.flush()
        alert_created = alert

    await db.commit()
    await db.refresh(detection)

    # 5. Broadcast en tiempo real vía WebSockets
    det_dict = {
        "id": detection.id,
        "latitude": detection.latitude,
        "longitude": detection.longitude,
        "altitude": detection.altitude,
        "speed": detection.speed,
        "heading": detection.heading,
        "threat_level": detection.threat_level.value,
        "is_drone": detection.is_drone,
        "ai_confidence": detection.ai_confidence,
        "status": detection.status.value,
    }
    await broadcast_detection(det_dict)

    if alert_created:
        await broadcast_alert({
            "id": alert_created.id,
            "title": alert_created.title,
            "message": alert_created.message,
            "severity": alert_created.severity.value,
            "type": alert_created.type.value,
            "detection_id": detection.id,
        })

    return {"status": "processed", "detection_id": detection.id, "alert_triggered": bool(alert_created)}

