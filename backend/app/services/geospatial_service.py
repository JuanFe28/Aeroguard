"""
AeroGuard — Geospatial Service (PostGIS & In-Memory Spatial Engine)
Calcula contención poligonal 2D (Point-in-Polygon), límites de altitud 3D,
distancias geodésicas y construye consultas espaciales nativas para PostGIS (OGC).
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple


class GeospatialService:
    """
    Servicio de cómputo geoespacial dual:
    1. Genera queries y expresiones OGC / WKT para PostGIS (ST_Contains, ST_MakePoint, ST_SetSRID).
    2. Ejecuta Ray-Casting Algorithm (Jordan Curve) y fórmulas geodésicas (Haversine)
       en memoria para entornos locales, tests y ejecución de alta frecuencia.
    """

    EARTH_RADIUS_METERS: float = 6371000.0

    @staticmethod
    def normalize_coordinates(raw_coords: Any) -> List[List[float]]:
        """
        Normaliza cualquier estructura de coordenadas a una lista de pares [[lat, lng], ...].
        Soporta diccionarios {'lat': x, 'lng': y} o tuplas/listas [lat, lng].
        """
        if not raw_coords:
            return []
        normalized: List[List[float]] = []
        for item in raw_coords:
            if isinstance(item, dict):
                lat = item.get("lat", item.get("latitude"))
                lng = item.get("lng", item.get("longitude"))
                if lat is not None and lng is not None:
                    normalized.append([float(lat), float(lng)])
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                normalized.append([float(item[0]), float(item[1])])
        return normalized

    @classmethod
    def to_wkt_polygon(cls, coordinates: Any) -> str:
        """
        Convierte coordenadas [[lat, lng], ...] en representación WKT (Well-Known Text).
        Cumple estándar OGC:
        - Orden de coordenadas: X Y (Longitude Latitude)
        - Anillo cerrado: el primer punto se repite al final.
        Ejemplo: POLYGON((-73.1848 7.1265, -73.1720 7.1350, ..., -73.1848 7.1265))
        """
        coords = cls.normalize_coordinates(coordinates)
        if len(coords) < 3:
            raise ValueError("Un polígono requiere al menos 3 vértices.")

        # PostGIS WKT espera (lng lat)
        wkt_points = [f"{pt[1]} {pt[0]}" for pt in coords]

        # Asegurar que el anillo esté cerrado
        if coords[0] != coords[-1]:
            wkt_points.append(f"{coords[0][1]} {coords[0][0]}")

        ring_str = ", ".join(wkt_points)
        return f"POLYGON(({ring_str}))"

    @classmethod
    def to_geojson_polygon(cls, coordinates: Any) -> Dict[str, Any]:
        """
        Convierte coordenadas [[lat, lng], ...] al formato GeoJSON Polygon oficial:
        {"type": "Polygon", "coordinates": [[[lng, lat], ..., [lng, lat]]]}
        """
        coords = cls.normalize_coordinates(coordinates)
        if len(coords) < 3:
            raise ValueError("Un polígono requiere al menos 3 vértices.")

        geojson_ring = [[pt[1], pt[0]] for pt in coords]
        if coords[0] != coords[-1]:
            geojson_ring.append([coords[0][1], coords[0][0]])

        return {
            "type": "Polygon",
            "coordinates": [geojson_ring]
        }

    @classmethod
    def build_postgis_containment_sql(
        cls,
        lat_param: str = ":lat",
        lng_param: str = ":lng",
        srid: int = 4326
    ) -> str:
        """
        Retorna la expresión SQL estándar de PostGIS para comprobar si un punto (lng, lat)
        está contenido dentro de una geometría 'geom' existente en la tabla:
        ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), :srid))
        """
        return f"ST_Contains(geom, ST_SetSRID(ST_MakePoint({lng_param}, {lat_param}), {srid}))"

    @classmethod
    def build_postgis_from_wkt_sql(
        cls,
        wkt_str: str,
        lat: float,
        lng: float,
        srid: int = 4326
    ) -> str:
        """
        Genera una consulta SQL independiente para evaluar si un punto específico
        está dentro de un polígono WKT usando funciones nativas PostGIS.
        """
        escaped_wkt = wkt_str.replace("'", "''")
        return (
            f"SELECT ST_Contains("
            f"ST_SetSRID(ST_GeomFromText('{escaped_wkt}', {srid}), {srid}), "
            f"ST_SetSRID(ST_MakePoint({lng}, {lat}), {srid})"
            f") AS is_inside;"
        )

    @classmethod
    def is_point_in_polygon(cls, lat: float, lng: float, polygon: Any) -> bool:
        """
        Algoritmo Ray-Casting (Jordan Curve Theorem):
        Determina si el punto (lat, lng) está estrictamente dentro del polígono.
        Soporta polígonos cóncavos, convexos y cualquier número de lados.
        """
        coords = cls.normalize_coordinates(polygon)
        if len(coords) < 3:
            return False

        # Si el último punto es igual al primero, removemos el duplicado para el ciclo
        if coords[0] == coords[-1] and len(coords) > 3:
            coords = coords[:-1]

        # Comprobar coincidencia exacta con vértices
        for p_lat, p_lng in coords:
            if abs(lat - p_lat) < 1e-9 and abs(lng - p_lng) < 1e-9:
                return True

        inside = False
        n = len(coords)
        j = n - 1

        for i in range(n):
            xi, yi = coords[i][1], coords[i][0]  # x = lng, y = lat
            xj, yj = coords[j][1], coords[j][0]

            # Ray-Casting horizontal a la derecha
            if (yi > lat) != (yj > lat):
                intersect_x = (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi
                if lng < intersect_x:
                    inside = not inside
            j = i

        return inside

    @classmethod
    def calculate_haversine_distance(
        cls,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calcula la distancia geodésica ortodrómica en metros entre dos puntos
        usando la fórmula del Haversine.
        """
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = (
            math.sin(dphi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return cls.EARTH_RADIUS_METERS * c

    @classmethod
    def distance_point_to_segment_m(
        cls,
        p_lat: float,
        p_lng: float,
        a_lat: float,
        a_lng: float,
        b_lat: float,
        b_lng: float
    ) -> float:
        """
        Calcula la distancia mínima en metros desde el punto P hasta el segmento de recta AB.
        """
        # Distancia entre A y B
        ab_dist = cls.calculate_haversine_distance(a_lat, a_lng, b_lat, b_lng)
        if ab_dist < 1e-6:
            return cls.calculate_haversine_distance(p_lat, p_lng, a_lat, a_lng)

        # Proyección planar aproximada a escala local (válido para distancias tácticas < 50 km)
        # Convertir a metros locales centrados en A
        lat_scale = 111320.0
        lng_scale = 111320.0 * math.cos(math.radians((a_lat + b_lat) / 2.0))

        ax, ay = 0.0, 0.0
        bx = (b_lng - a_lng) * lng_scale
        by = (b_lat - a_lat) * lat_scale
        px = (p_lng - a_lng) * lng_scale
        py = (p_lat - a_lat) * lat_scale

        seg_len_sq = bx * bx + by * by
        if seg_len_sq < 1e-6:
            return cls.calculate_haversine_distance(p_lat, p_lng, a_lat, a_lng)

        # Factor de proyección t en [0, 1]
        t = max(0.0, min(1.0, (px * bx + py * by) / seg_len_sq))
        proj_x = ax + t * bx
        proj_y = ay + t * by

        dist = math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)
        return dist

    @classmethod
    def calculate_distance_to_polygon_boundary_m(
        cls,
        lat: float,
        lng: float,
        polygon: Any
    ) -> float:
        """
        Calcula la distancia mínima en metros desde un punto a la frontera del polígono.
        Si el punto está en el borde, retorna ~0.0.
        """
        coords = cls.normalize_coordinates(polygon)
        if len(coords) < 3:
            return 0.0

        min_dist = float("inf")
        n = len(coords)
        for i in range(n):
            j = (i + 1) % n
            dist = cls.distance_point_to_segment_m(
                lat, lng,
                coords[i][0], coords[i][1],
                coords[j][0], coords[j][1]
            )
            if dist < min_dist:
                min_dist = dist

        return round(min_dist, 2)

    @classmethod
    def evaluate_zone_breach(
        cls,
        lat: float,
        lng: float,
        alt: float,
        zone: Any
    ) -> Dict[str, Any]:
        """
        Evalúa si un vehículo aéreo invade una zona de exclusión en 3D (Polígono 2D + Altitud).
        
        Retorna:
            {
                "zone_id": str,
                "zone_name": str,
                "threat_level": str,
                "in_polygon_2d": bool,
                "in_altitude_range": bool,
                "is_breached": bool,
                "min_altitude": float,
                "max_altitude": float,
                "current_altitude": float,
                "distance_to_boundary_m": float,
            }
        """
        coords = cls.normalize_coordinates(getattr(zone, "coordinates", None) or [])
        in_polygon = cls.is_point_in_polygon(lat, lng, coords)
        
        min_alt = float(getattr(zone, "min_altitude", 0.0) or 0.0)
        configured_max = getattr(zone, "max_altitude", None)
        max_alt = 500.0 if configured_max is None else float(configured_max)
        in_altitude = (min_alt <= alt <= max_alt)

        is_breached = in_polygon and in_altitude
        dist_boundary = cls.calculate_distance_to_polygon_boundary_m(lat, lng, coords)

        threat_val = getattr(zone, "threat_level", "high")
        if hasattr(threat_val, "value"):
            threat_val = threat_val.value

        zone_id = str(getattr(zone, "id", ""))
        zone_name = str(getattr(zone, "name", "Zona Desconocida"))

        return {
            "zone_id": zone_id,
            "zone_name": zone_name,
            "threat_level": str(threat_val),
            "in_polygon_2d": in_polygon,
            "in_altitude_range": in_altitude,
            "is_breached": is_breached,
            "min_altitude": min_alt,
            "max_altitude": max_alt,
            "current_altitude": alt,
            "distance_to_boundary_m": dist_boundary,
        }

    @classmethod
    def evaluate_all_zones(
        cls,
        lat: float,
        lng: float,
        alt: float,
        zones: Any
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Evalúa la posición de una aeronave contra una colección de zonas restringidas activas.
        
        Retorna:
            (lista_de_todas_las_invasiones_activas, invasion_de_mayor_prioridad)
        """
        active_breaches: List[Dict[str, Any]] = []
        severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}

        for zone in zones:
            if hasattr(zone, "is_active") and not zone.is_active:
                continue

            result = cls.evaluate_zone_breach(lat, lng, alt, zone)
            if result["is_breached"]:
                active_breaches.append(result)

        if not active_breaches:
            return [], None

        # Ordenar por severidad más alta
        highest_breach = max(
            active_breaches,
            key=lambda b: severity_rank.get(b["threat_level"].lower(), 0)
        )
        return active_breaches, highest_breach


geospatial_service = GeospatialService()
