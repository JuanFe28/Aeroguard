"""
AeroGuard — Restricted Zones Endpoint (RF-017 a RF-019, RF-012)
Definición, delimitación geográfica poligonal, administración y verificación geoespacial
de zonas de exclusión aérea compatibles con PostGIS (OGC WKT / GeoJSON).
"""

from typing import List, Optional, Any, Dict
import math
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.models import RestrictedZone, ThreatLevel
from app.services.geospatial_service import geospatial_service

router = APIRouter()
logger = structlog.get_logger("AeroGuard-Zones")


def _normalize_coordinates(raw_coords: Any) -> list:
    """Normaliza coordenadas a formato [[lat, lng], ...]."""
    try:
        coordinates = geospatial_service.normalize_coordinates(raw_coords)
    except (ValueError, TypeError, OverflowError):
        raise HTTPException(status_code=422, detail="Coordenadas geográficas inválidas.")
    if raw_coords is not None and len(coordinates) != len(raw_coords):
        raise HTTPException(status_code=422, detail="Cada vértice requiere latitud y longitud.")
    return coordinates


def _validate_zone(min_altitude, max_altitude, coordinates, is_active):
    if (min_altitude is None or max_altitude is None
            or not math.isfinite(min_altitude) or not math.isfinite(max_altitude)
            or not 0 <= min_altitude <= max_altitude <= 15000):
        raise HTTPException(status_code=422, detail="Rango de altitud inválido (0–15000 m).")
    for point in coordinates:
        if not (len(point) == 2 and all(math.isfinite(v) for v in point)
                and -90 <= point[0] <= 90 and -180 <= point[1] <= 180):
            raise HTTPException(status_code=422, detail="Coordenadas geográficas inválidas.")
    if is_active and len({tuple(point) for point in coordinates}) < 3:
        raise HTTPException(status_code=422, detail="Una zona activa requiere al menos tres vértices distintos.")


def _threat_level_to_color(level: Any) -> str:
    mapping = {
        ThreatLevel.CRITICAL: "#ef4444",
        ThreatLevel.HIGH:     "#f59e0b",
        ThreatLevel.MEDIUM:   "#3b82f6",
        ThreatLevel.LOW:      "#10b981",
        "critical":           "#ef4444",
        "high":               "#f59e0b",
        "medium":             "#3b82f6",
        "low":                "#10b981",
    }
    return mapping.get(level, "#ef4444")


def _serialize_zone(z: RestrictedZone) -> Dict[str, Any]:
    """Serializa modelo RestrictedZone con metadatos espaciales WKT y GeoJSON."""
    coords: list = list(z.coordinates or [])  # type: ignore
    wkt_polygon = None
    geojson_polygon = None
    try:
        if len(coords) >= 3:
            wkt_polygon = geospatial_service.to_wkt_polygon(coords)
            geojson_polygon = geospatial_service.to_geojson_polygon(coords)
    except Exception as error:
        logger.warning("No se pudieron serializar las coordenadas de la zona", error=str(error))

    threat_str = z.threat_level.value if hasattr(z.threat_level, "value") else str(z.threat_level)

    return {
        "id": z.id,
        "name": z.name,
        "description": z.description,
        "threat_level": threat_str,
        "severity": threat_str,
        "color": z.color or _threat_level_to_color(z.threat_level),
        "max_altitude": z.max_altitude,
        "min_altitude": z.min_altitude,
        "coordinates": coords,
        "polygon": coords,
        "wkt": wkt_polygon,
        "geojson": geojson_polygon,
        "is_active": z.is_active,
        "created_at": z.created_at.isoformat() if z.created_at else None,
        "updated_at": z.updated_at.isoformat() if z.updated_at else None,
    }


class ZoneCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    threat_level: Optional[ThreatLevel] = None
    severity: Optional[str] = None
    color: Optional[str] = Field(default=None, pattern=r'^#[0-9a-fA-F]{6}$')
    max_altitude: float = 500.0
    min_altitude: float = 0.0
    coordinates: Optional[list] = None
    polygon: Optional[list] = None
    is_active: bool = True


class ZoneUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    threat_level: Optional[ThreatLevel] = None
    severity: Optional[str] = None
    color: Optional[str] = Field(default=None, pattern=r'^#[0-9a-fA-F]{6}$')
    max_altitude: Optional[float] = None
    min_altitude: Optional[float] = None
    coordinates: Optional[list] = None
    polygon: Optional[list] = None
    is_active: Optional[bool] = None


class ZoneBreachCheckRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitud WGS84")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitud WGS84")
    altitude: float = Field(0.0, ge=0.0, le=15000.0, description="Altitud en metros sobre el nivel del suelo")
    zone_id: Optional[str] = Field(None, description="ID opcional para evaluar una zona puntual")


@router.get("", summary="Listar zonas restringidas (RF-017)")
async def list_zones(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("zones:read")),
):
    """Lista todas las zonas restringidas configuradas con representaciones geoespaciales WKT y GeoJSON."""
    query = select(RestrictedZone).order_by(RestrictedZone.name.asc())
    result = await db.execute(query)
    zones = result.scalars().all()
    return [_serialize_zone(z) for z in zones]


@router.post("/check-breach", summary="Verificación geoespacial de invasión de zona (RF-012, RF-017)")
async def check_zone_breach(
    body: ZoneBreachCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("zones:read")),
):
    """
    Evalúa la posición 3D (latitud, longitud, altitud) contra zonas de exclusión aéreas.
    Utiliza el motor geoespacial de alta precisión (PostGIS ST_Contains / Ray-Casting Algorithm).
    """
    if body.zone_id:
        query = select(RestrictedZone).where(RestrictedZone.id == body.zone_id)
        result = await db.execute(query)
        zone = result.scalar_one_or_none()
        if not zone:
            raise HTTPException(status_code=404, detail="Zona restringida no encontrada.")

        evaluation = geospatial_service.evaluate_zone_breach(
            body.latitude,
            body.longitude,
            body.altitude,
            zone,
        )
        is_breach = evaluation["is_breached"]
        return {
            "is_breach": is_breach,
            "breaches_count": 1 if is_breach else 0,
            "evaluated_position": {
                "latitude": body.latitude,
                "longitude": body.longitude,
                "altitude": body.altitude,
            },
            "highest_breach": evaluation if is_breach else None,
            "breached_zones": [evaluation] if is_breach else [],
            "zone_details": _serialize_zone(zone),
            "postgis_point_wkt": f"POINT({body.longitude} {body.latitude})",
            "message": (
                f"Incursión detectada en zona '{zone.name}'"
                if is_breach
                else f"Vuelo nominal respecto a zona '{zone.name}'"
            ),
        }

    # Evaluar contra todas las zonas activas
    query = select(RestrictedZone).where(RestrictedZone.is_active == True)
    from app.core.spatial import zone_candidates
    query = await zone_candidates(db, query, body.latitude, body.longitude)
    result = await db.execute(query)
    zones = result.scalars().all()

    active_breaches, highest_breach = geospatial_service.evaluate_all_zones(
        body.latitude,
        body.longitude,
        body.altitude,
        zones,
    )

    return {
        "is_breach": bool(active_breaches),
        "breaches_count": len(active_breaches),
        "evaluated_position": {
            "latitude": body.latitude,
            "longitude": body.longitude,
            "altitude": body.altitude,
        },
        "highest_breach": highest_breach,
        "breached_zones": active_breaches,
        "postgis_point_wkt": f"POINT({body.longitude} {body.latitude})",
        "message": (
            f"Alerta: Incursión detectada en {len(active_breaches)} zona(s) protegida(s)."
            if active_breaches
            else "Vuelo nominal: Posición fuera de zonas de exclusión protegidas."
        ),
    }


@router.post("", status_code=status.HTTP_201_CREATED, summary="Crear zona restringida (RF-017)")
async def create_zone(
    body: ZoneCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("zones:write")),
):
    """Crea una nueva zona geográfica restringida con polígono de coordenadas."""
    # Resolver nivel de amenaza
    threat = body.threat_level
    if not threat and body.severity:
        try:
            threat = ThreatLevel(body.severity.lower())
        except ValueError:
            threat = ThreatLevel.HIGH
    if not threat:
        threat = ThreatLevel.HIGH

    # Resolver coordenadas
    raw_coords = body.coordinates if body.coordinates is not None else body.polygon
    coords = _normalize_coordinates(raw_coords)
    _validate_zone(body.min_altitude, body.max_altitude, coords, body.is_active)

    # Color
    color = body.color or _threat_level_to_color(threat)

    zone = RestrictedZone(
        name=body.name,
        description=body.description,
        threat_level=threat,
        color=color,
        max_altitude=body.max_altitude,
        min_altitude=body.min_altitude,
        coordinates=coords,
        is_active=body.is_active,
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)

    return _serialize_zone(zone)


@router.get("/{zone_id}", summary="Detalle de zona restringida")
async def get_zone(
    zone_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("zones:read")),
):
    """Obtiene el detalle de una zona por ID incluyendo WKT y GeoJSON."""
    query = select(RestrictedZone).where(RestrictedZone.id == zone_id)
    result = await db.execute(query)
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona restringida no encontrada.")

    return _serialize_zone(zone)


@router.put("/{zone_id}", summary="Actualizar zona restringida")
async def update_zone(
    zone_id: str,
    body: ZoneUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("zones:write")),
):
    """Actualiza los parámetros o polígono de una zona."""
    query = select(RestrictedZone).where(RestrictedZone.id == zone_id)
    result = await db.execute(query)
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona restringida no encontrada.")

    update_dict = body.model_dump(exclude_unset=True)

    # Procesar threat_level / severity
    if "severity" in update_dict and "threat_level" not in update_dict:
        try:
            update_dict["threat_level"] = ThreatLevel(update_dict["severity"].lower())
        except ValueError:
            pass
    update_dict.pop("severity", None)

    # Procesar polygon / coordinates
    if "polygon" in update_dict:
        update_dict["coordinates"] = _normalize_coordinates(update_dict.pop("polygon"))
    elif "coordinates" in update_dict:
        update_dict["coordinates"] = _normalize_coordinates(update_dict["coordinates"])

    _validate_zone(
        update_dict.get("min_altitude", zone.min_altitude),
        update_dict.get("max_altitude", zone.max_altitude),
        update_dict.get("coordinates", zone.coordinates) or [],
        update_dict.get("is_active", zone.is_active),
    )

    for field, val in update_dict.items():
        if hasattr(zone, field):
            setattr(zone, field, val)

    await db.commit()
    await db.refresh(zone)

    return _serialize_zone(zone)


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar zona")
async def delete_zone(
    zone_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("zones:delete")),
):
    """Elimina una zona restringida."""
    query = select(RestrictedZone).where(RestrictedZone.id == zone_id)
    result = await db.execute(query)
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona restringida no encontrada.")

    await db.delete(zone)
    await db.commit()
