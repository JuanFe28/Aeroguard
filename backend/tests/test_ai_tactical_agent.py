"""
Tests para Agente IA de Análisis Táctico y Webhook SOAR / n8n (HU-03 / [CODE-05])
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ai_tactical_agent_service import ai_tactical_service
from app.core.security import create_access_token

client = TestClient(app)
AUTH = {"Authorization": "Bearer " + create_access_token({"sub": "admin", "role": "admin"})}


def test_embedded_ai_tactical_agent_verdict_rules():
    """Valida que el motor táctico embebido genere dictámenes militares C-UAS conformes."""
    drone_data = {
        "drone_id": "UAV-ROGUE-99",
        "latitude": 7.1195,
        "longitude": -73.1230,
        "altitude_m": 155.0,
        "speed_ms": 18.5,
        "heading_deg": 180.0,
        "ai_confidence": 0.96
    }
    zone_data = {
        "name": "Complejo Militar UTS",
        "max_allowed_altitude_m": 120.0,
        "restriction_type": "NO_FLY_ZONE"
    }

    verdict, threat = ai_tactical_service._generate_embedded_tactical_verdict(drone_data, zone_data)
    assert threat == "CRITICAL"
    assert "UAV-ROGUE-99" in verdict
    assert "155m" in verdict
    assert "120m" in verdict
    assert "responsable de seguridad" in verdict
    assert "inhibición RF" not in verdict
    # Validar longitud máxima militar concisa (menos de 55 palabras)
    words = verdict.split()
    assert len(words) < 55


def test_trigger_incident_endpoint_success():
    """Valida la invocación del endpoint /trigger-incident y su despacho."""
    payload = {
        "event_type": "GEOFENCE_BREACH_CRITICAL",
        "incident_id": "INC-TEST-SOAR-001",
        "drone": {
            "drone_id": "UAV-HK-TEST",
            "latitude": 7.1200,
            "longitude": -73.1210,
            "altitude_m": 170.0,
            "speed_ms": 21.0,
            "heading_deg": 90.0,
            "ai_confidence": 0.98
        },
        "zone": {
            "name": "Zona Crítica Bucaramanga",
            "max_allowed_altitude_m": 120.0,
            "restriction_type": "NO_FLY_ZONE"
        }
    }

    response = client.post("/api/v1/alerts/trigger-incident", json=payload, headers=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["incident_id"] == "INC-TEST-SOAR-001"
    assert data["data"]["threat_level"] == "CRITICAL"
    assert "responsable de seguridad" in data["data"]["ai_verdict"]

    # Validar que /ai-verdict refleja de inmediato el nuevo incidente analizado
    get_res = client.get("/api/v1/alerts/ai-verdict", headers=AUTH)
    assert get_res.status_code == 200
    assert get_res.json()["incident_id"] == "INC-TEST-SOAR-001"
    assert get_res.json()["drone_id"] == "UAV-HK-TEST"
