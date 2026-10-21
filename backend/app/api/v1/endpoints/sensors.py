"""
AeroGuard — Sensors Endpoint (RF-020 a RF-023)
Gestión, configuración y monitoreo del estado de sensores físicos o simulados.
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from uuid import UUID
from app.core.config import settings

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.models import Sensor, SensorType, SensorStatus

router = APIRouter()


class SensorCreateSchema(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=128)
    type: SensorType = SensorType.RADAR
    status: SensorStatus = SensorStatus.ACTIVE
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude: float = Field(default=0, ge=0, le=15000)
    range_km: float = Field(default=5, gt=0, le=1000)
    config: dict = {}


class SensorUpdateSchema(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    type: Optional[SensorType] = None
    status: Optional[SensorStatus] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    altitude: Optional[float] = Field(default=None, ge=0, le=15000)
    range_km: Optional[float] = Field(default=None, gt=0, le=1000)
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
    model_config = ConfigDict(allow_inf_nan=False)
    sensor_id: str = Field(min_length=1, max_length=128)
    object_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    latitude: float
    longitude: float
    altitude: float
    speed: float
    heading: float = Field(ge=0, le=360)
    timestamp: Optional[datetime] = None
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

    from app.models.models import Detection, TrajectoryPoint, Alert, RestrictedZone, DetectionStatus, ThreatLevel, AlertSeverity, AlertType, SensorTrack, AlertStatus
    from app.api.v1.endpoints.websocket import broadcast_detection, broadcast_alert
    from app.services.geospatial_service import geospatial_service

    from app.api.v1.endpoints.config import load_persisted_config
    await load_persisted_config(db)
    if packet.altitude > settings.DETECTION_MAX_ALTITUDE or not settings.DETECTION_MIN_SPEED <= packet.speed <= settings.DETECTION_MAX_SPEED:
        raise HTTPException(status_code=400, detail="Telemetría fuera de los umbrales configurados.")
    try:
        sensor_uuid = str(UUID(packet.sensor_id))
    except ValueError:
        sensor_uuid = None
    predicate = Sensor.id == sensor_uuid if sensor_uuid else Sensor.name == packet.sensor_id
    sensor = (await db.execute(select(Sensor).where(predicate).with_for_update())).scalar_one_or_none()
    if sensor is None:
        # El registro automático está limitado a la exposición local explícita.
        if not (settings.APP_ENV == 'development' and settings.SEED_DEMO_DATA):
            raise HTTPException(status_code=404, detail="Registra el sensor antes de enviar telemetría.")
        sensor = Sensor(name=packet.sensor_id, latitude=packet.latitude, longitude=packet.longitude)
        db.add(sensor)
        await db.flush()
    if sensor.status != SensorStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="El sensor no está activo.")
    await db.execute(update(Sensor).where(Sensor.id == sensor.id).values(last_active=datetime.now(timezone.utc)))
    track = await db.get(SensorTrack, (sensor.id, packet.object_id)) if packet.object_id else None
    detection = await db.get(Detection, track.detection_id) if track else None
    if detection and detection.status not in (DetectionStatus.ACTIVE, DetectionStatus.PENDING):
        detection = None
    is_new = detection is None
    if is_new:
        detection = Detection(
        sensor_id=sensor.id,
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
    else:
        for key in ('latitude', 'longitude', 'altitude', 'speed', 'heading'):
            setattr(detection, key, getattr(packet, key))
    detection.zone_id = None
    await db.flush()
    if is_new:
        await db.execute(update(Sensor).where(Sensor.id == sensor.id).values(detections_count=Sensor.detections_count + 1))
        if packet.object_id:
            if track:
                track.detection_id = detection.id
            else:
                db.add(SensorTrack(sensor_id=sensor.id, object_key=packet.object_id, detection_id=detection.id))

    # 3. Guardar punto de trayectoria
    point = TrajectoryPoint(
        sequence=(await db.execute(select(func.count()).select_from(TrajectoryPoint).where(TrajectoryPoint.detection_id == detection.id))).scalar_one(),
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
    from app.core.spatial import zone_candidates
    zones_query = await zone_candidates(db, zones_query, packet.latitude, packet.longitude)
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

        existing_alert = (await db.execute(select(Alert.id).where(Alert.detection_id == detection.id, Alert.type == AlertType.RESTRICTED_ZONE, Alert.status.in_([AlertStatus.OPEN, AlertStatus.ASSIGNED])).limit(1))).scalar_one_or_none()
        if settings.ALERTS_ENABLED and existing_alert is None:
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

