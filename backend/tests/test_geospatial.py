"""
Tests para Motor Geoespacial PostGIS y Algoritmo Ray-Casting 3D ([CODE-06] / RF-012 / RF-017)
Valida Point-in-Polygon (Jordan Curve), PostGIS WKT/GeoJSON, envoltura altimétrica 3D,
y endpoints de verificación de incursión en zonas de exclusión aérea.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.services.geospatial_service import geospatial_service


@pytest.fixture
def client():
    """TestClient con ciclo de vida lifespan activo (garantiza base de datos lista con fallback SQLite)."""
    with TestClient(app) as c:
        yield c


# ============================================================
# 1. Pruebas Unitarias de Algoritmo Ray-Casting (Point-in-Polygon)
# ============================================================

def test_ray_casting_convex_polygon():
    """Valida la detección en un polígono rectangular regular (Bucaramanga centro)."""
    # Polígono: [lat, lng]
    polygon = [
        [7.1000, -73.1500],
        [7.1000, -73.1000],
        [7.1500, -73.1000],
        [7.1500, -73.1500]
    ]

    # Punto interior
    assert geospatial_service.is_point_in_polygon(7.1250, -73.1250, polygon) is True

    # Puntos exteriores (norte, sur, este, oeste)
    assert geospatial_service.is_point_in_polygon(7.1600, -73.1250, polygon) is False
    assert geospatial_service.is_point_in_polygon(7.0900, -73.1250, polygon) is False
    assert geospatial_service.is_point_in_polygon(7.1250, -73.0900, polygon) is False
    assert geospatial_service.is_point_in_polygon(7.1250, -73.1600, polygon) is False

    # Vértice exacto
    assert geospatial_service.is_point_in_polygon(7.1000, -73.1500, polygon) is True


def test_ray_casting_concave_polygon():
    """Valida la detección en polígonos cóncavos (ej. forma de L)."""
    # Polígono en forma de 'L'
    l_polygon = [
        [0.0, 0.0],
        [0.0, 3.0],
        [1.0, 3.0],
        [1.0, 1.0],
        [3.0, 1.0],
        [3.0, 0.0]
    ]

    # Punto en el brazo vertical (interior)
    assert geospatial_service.is_point_in_polygon(0.5, 2.0, l_polygon) is True

    # Punto en el brazo horizontal (interior)
    assert geospatial_service.is_point_in_polygon(2.0, 0.5, l_polygon) is True

    # Punto en la muesca cóncava vacía (exterior, (2.0, 2.0))
    assert geospatial_service.is_point_in_polygon(2.0, 2.0, l_polygon) is False

    # Punto exterior lejano
    assert geospatial_service.is_point_in_polygon(4.0, 4.0, l_polygon) is False


def test_ray_casting_closed_ring_tolerance():
    """Valida que un polígono con o sin repetición del vértice inicial devuelva el mismo resultado."""
    open_poly = [[1.0, 1.0], [1.0, 5.0], [5.0, 5.0], [5.0, 1.0]]
    closed_poly = [[1.0, 1.0], [1.0, 5.0], [5.0, 5.0], [5.0, 1.0], [1.0, 1.0]]

    assert geospatial_service.is_point_in_polygon(3.0, 3.0, open_poly) is True
    assert geospatial_service.is_point_in_polygon(3.0, 3.0, closed_poly) is True
    assert geospatial_service.is_point_in_polygon(6.0, 6.0, open_poly) is False
    assert geospatial_service.is_point_in_polygon(6.0, 6.0, closed_poly) is False


# ============================================================
# 2. Pruebas de Serialización OGC / PostGIS (WKT y GeoJSON)
# ============================================================

def test_wkt_and_geojson_generation():
    """Valida que las coordenadas [[lat, lng], ...] se conviertan correctamente a WKT (lng lat) y GeoJSON."""
    coords = [
        [7.1265, -73.1848],
        [7.1350, -73.1720],
        [7.1210, -73.1650]
    ]

    wkt = geospatial_service.to_wkt_polygon(coords)
    # WKT debe tener el orden X (lng) Y (lat) y cerrar el polígono
    assert wkt.startswith("POLYGON((")
    assert wkt.endswith("))")
    assert "-73.1848 7.1265" in wkt
    # El primer punto debe repetirse al final para cerrar el anillo OGC
    assert wkt.endswith("-73.1848 7.1265))")

    geojson = geospatial_service.to_geojson_polygon(coords)
    assert geojson["type"] == "Polygon"
    assert len(geojson["coordinates"]) == 1
    # GeoJSON anillo cerrado: 4 puntos (3 vertices + cierre)
    assert len(geojson["coordinates"][0]) == 4
    assert geojson["coordinates"][0][0] == [-73.1848, 7.1265]
    assert geojson["coordinates"][0][-1] == [-73.1848, 7.1265]


def test_wkt_invalid_polygon_raises_error():
    """Valida que polígonos degenerados con menos de 3 puntos lancen ValueError."""
    with pytest.raises(ValueError, match="al menos 3 vértices"):
        geospatial_service.to_wkt_polygon([[7.0, -73.0], [7.1, -73.1]])


# ============================================================
# 3. Pruebas de Constructores SQL PostGIS
# ============================================================

def test_postgis_sql_clause_builders():
    """Valida la formulación sintáctica de expresiones espaciales para PostgreSQL/PostGIS."""
    sql_clause = geospatial_service.build_postgis_containment_sql(":lat", ":lng", 4326)
    assert "ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))" == sql_clause

    wkt_test = "POLYGON((-74.15 4.69, -74.13 4.71, -74.12 4.70, -74.15 4.69))"
    standalone_sql = geospatial_service.build_postgis_from_wkt_sql(wkt_test, 4.70, -74.14, 4326)
    assert "ST_GeomFromText" in standalone_sql
    assert "ST_MakePoint(-74.14, 4.7)" in standalone_sql
    assert "4326" in standalone_sql


# ============================================================
# 4. Pruebas de Distancia Geodésica Haversine y Fronteras
# ============================================================

def test_haversine_distance():
    """Valida cálculo de distancia ortodrómica entre Bucaramanga y Bogotá (~300 km en línea recta)."""
    bga_lat, bga_lng = 7.1193, -73.1227
    bog_lat, bog_lng = 4.7110, -74.0721

    dist_m = geospatial_service.calculate_haversine_distance(bga_lat, bga_lng, bog_lat, bog_lng)
    dist_km = dist_m / 1000.0

    # Distancia real aproximada entre ambas ciudades: ~280 - 320 km
    assert 270.0 < dist_km < 330.0


# ============================================================
# 5. Pruebas de Evaluación de Invasión 3D (Polígono + Altitud)
# ============================================================

class MockZone:
    def __init__(self, id, name, threat_level, min_altitude, max_altitude, coordinates, is_active=True):
        self.id = id
        self.name = name
        self.threat_level = threat_level
        self.min_altitude = min_altitude
        self.max_altitude = max_altitude
        self.coordinates = coordinates
        self.is_active = is_active


def test_evaluate_zone_breach_3d():
    """Valida la invasión tridimensional: 2D dentro del polígono pero verificando techo altimétrico."""
    # Zona con techo de 120m
    zone = MockZone(
        id="zone-palonegro-test",
        name="Zona Crítica Palonegro",
        threat_level="critical",
        min_altitude=0.0,
        max_altitude=120.0,
        coordinates=[
            [7.1200, -73.1800],
            [7.1300, -73.1800],
            [7.1300, -73.1700],
            [7.1200, -73.1700]
        ]
    )

    # Caso 1: Punto adentro y altitud 80m (< 120m) -> INVASIÓN CONFIRMADA
    res1 = geospatial_service.evaluate_zone_breach(7.1250, -73.1750, 80.0, zone)
    assert res1["in_polygon_2d"] is True
    assert res1["in_altitude_range"] is True
    assert res1["is_breached"] is True
    assert res1["threat_level"] == "critical"

    # Caso 2: Punto adentro pero altitud 180m (> 120m) -> FUERA DE RANGO DE ALTITUD (NO BREACH)
    res2 = geospatial_service.evaluate_zone_breach(7.1250, -73.1750, 180.0, zone)
    assert res2["in_polygon_2d"] is True
    assert res2["in_altitude_range"] is False
    assert res2["is_breached"] is False

    # Caso 3: Punto afuera 2D con altitud 80m -> FUERA DE ZONA (NO BREACH)
    res3 = geospatial_service.evaluate_zone_breach(7.2000, -73.1000, 80.0, zone)
    assert res3["in_polygon_2d"] is False
    assert res3["is_breached"] is False


# ============================================================
# 6. Pruebas de Integración con API: POST /api/v1/zones/check-breach
# ============================================================

def test_api_check_breach_active_zones(client: TestClient):
    """Valida el endpoint /api/v1/zones/check-breach con una posición que invade zona de Palonegro."""
    token = create_access_token({"sub": "operator_test", "role": "operator"})

    # Coordenada dentro de Palonegro (definida en init.sql):
    # Coords: [[7.1265,-73.1848],[7.1350,-73.1720],[7.1210,-73.1650],[7.1140,-73.1780]]
    # Centro aproximado: lat=7.1240, lng=-73.1750, alt=150m (techo es 1200m)
    response = client.post(
        "/api/v1/zones/check-breach",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "latitude": 7.1240,
            "longitude": -73.1750,
            "altitude": 150.0
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "is_breach" in data
    assert "postgis_point_wkt" in data
    assert data["postgis_point_wkt"] == "POINT(-73.175 7.124)"
    assert data["is_breach"] is True
    assert data["breaches_count"] >= 1
    assert "Aeropuerto Palonegro" in data["highest_breach"]["zone_name"]


def test_api_check_breach_outside_all_zones(client: TestClient):
    """Valida que una posición lejana devuelva is_breach=False y mensaje de vuelo nominal."""
    token = create_access_token({"sub": "operator_test", "role": "operator"})

    response = client.post(
        "/api/v1/zones/check-breach",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "latitude": -12.0000,
            "longitude": -45.0000,
            "altitude": 100.0
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_breach"] is False
    assert data["breaches_count"] == 0
    assert "Vuelo nominal" in data["message"]


def test_api_check_breach_unauthorized(client: TestClient):
    """Valida que el endpoint requiera token de autenticación válido."""
    response = client.post(
        "/api/v1/zones/check-breach",
        json={"latitude": 7.1240, "longitude": -73.1750, "altitude": 100.0}
    )
    assert response.status_code == 401


# ============================================================
# 7. Pruebas de Integración con Telemetría de Sensores
# ============================================================

def test_sensor_telemetry_triggers_geospatial_breach(client: TestClient):
    """Valida que un paquete de telemetría emitido en zona restringida dispare alerta con zona asociada."""
    payload = {
        "sensor_id": "RADAR-TEST-01",
        "latitude": 7.1240,
        "longitude": -73.1750,
        "altitude": 110.0,
        "speed": 65.0,
        "heading": 180.0
    }

    response = client.post("/api/v1/sensors/telemetry", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "processed"
    assert data["alert_triggered"] is True
    assert "detection_id" in data
