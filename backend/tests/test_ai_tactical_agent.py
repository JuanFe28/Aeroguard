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

@pytest.mark.parametrize("altitude,confidence,action,level", [
    (135.0, 0.95, "NOTIFICAR_Y_VERIFICAR", "CRITICAL"),
    (135.0, 0.20, "VERIFICAR_DETECCION", "MEDIUM"),
    (80.0, 0.90, "MONITOREAR", "LOW"),
])
def test_goal_based_response_visible_in_endpoint_and_latest_verdict(
    isolated_client, monkeypatch, altitude, confidence, action, level
):
    """Prueba HTTP: el modelo decide, comunica y deja consultar el dictamen."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "SOAR_AI_AGENT_ENABLED", False)
    payload = {
        "incident_id": f"TEST-GOALS-{altitude}-{confidence}",
        "drone": {
            "drone_id": "OBJETO-DE-PRUEBA", "latitude": 7.12, "longitude": -73.12,
            "altitude_m": altitude, "speed_ms": 10, "heading_deg": 90,
            "ai_confidence": confidence,
        },
        "zone": {"name": "Zona de prueba", "max_allowed_altitude_m": 120},
    }
    response = isolated_client.post("/api/v1/alerts/trigger-incident", json=payload, headers=AUTH)
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["goal_decision"]["action"] == action
    assert result["threat_level"] == level
    assert result["execution_source"] == "goal_based_local"
    assert result["goal_decision"]["evidence"]
    assert result["goal_decision"]["human_review_required"] is True

    latest = isolated_client.get("/api/v1/alerts/ai-verdict", headers=AUTH)
    assert latest.status_code == 200
    assert latest.json()["goal_decision"]["action"] == action
    assert latest.json()["incident_id"] == result["incident_id"]


@pytest.mark.parametrize("altitude,confidence,action,priority,level", [
    (135.0, 0.95, "NOTIFICAR_Y_VERIFICAR", "CRITICAL", "CRITICAL"),
    (135.0, 0.20, "VERIFICAR_DETECCION", "REVIEW", "MEDIUM"),
    (80.0, 0.90, "MONITOREAR", "NORMAL", "LOW"),
])
def test_goal_demo_is_read_only_and_no_side_effects(
    isolated_client, monkeypatch, altitude, confidence, action, priority, level
):
    """El laboratorio consulta el modelo sin generar una alerta o reemplazar el dictamen."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "SOAR_AI_AGENT_ENABLED", True)

    verdict_before = isolated_client.get("/api/v1/alerts/ai-verdict", headers=AUTH)
    alerts_before = isolated_client.get("/api/v1/alerts", headers=AUTH)
    assert verdict_before.status_code == 200
    assert alerts_before.status_code == 200

    scenario = {
        "incident_id": f"SIM-TEST-{altitude}-{confidence}",
        "event_type": "GOAL_BASED_CLASSROOM_DEMO",
        "drone": {
            "drone_id": "OBJETO-SINTETICO", "latitude": 7.12, "longitude": -73.12,
            "altitude_m": altitude, "speed_ms": 10, "heading_deg": 90,
            "ai_confidence": confidence,
        },
        "zone": {
            "name": "Zona sintética", "max_allowed_altitude_m": 120,
            "restriction_type": "NO_FLY_ZONE",
        },
    }
    response = isolated_client.post("/api/v1/alerts/evaluate-goals", json=scenario, headers=AUTH)
    assert response.status_code == 200
    result = response.json()
    assert result["simulation"] is True
    assert result["data"]["goal_decision"]["action"] == action
    assert result["data"]["goal_decision"]["priority"] == priority
    assert result["data"]["threat_level"] == level
    assert result["data"]["execution_source"] == "goal_based_simulation"
    assert result["data"]["goal_decision"]["human_review_required"] is True

    assert isolated_client.get("/api/v1/alerts/ai-verdict", headers=AUTH).json() == verdict_before.json()
    assert isolated_client.get("/api/v1/alerts", headers=AUTH).json() == alerts_before.json()


def test_goal_demo_requires_authenticated_user(isolated_client):
    response = isolated_client.post("/api/v1/alerts/evaluate-goals", json={})
    assert response.status_code in (401, 403)
