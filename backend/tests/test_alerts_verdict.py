"""
Tests para endpoints de Dictamen Táctico de IA (HU-03 / [CODE-03])
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)
AUTH = {"Authorization": "Bearer " + create_access_token({"sub": "admin", "role": "admin"})}


def test_get_ai_verdict_success():
    """Valida obtención del dictamen táctico de IA actual."""
    response = client.get("/api/v1/alerts/ai-verdict", headers=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert "incident_id" in data
    assert "ai_verdict" in data
    assert "threat_level" in data
    assert "drone_id" in data
    assert "120m" in data["ai_verdict"] or "UAV" in data["drone_id"]


def test_post_ai_verdict_broadcast():
    """Valida registro y actualización de nuevo dictamen desde workflow SOAR / n8n."""
    payload = {
        "incident_id": "INC-TEST-9999",
        "ai_verdict": "Intrusión confirmada a 160m de altura sobre zona militar. Alerta máxima.",
        "drone_id": "UAV-ROGUE-01",
        "threat_level": "CRITICAL"
    }
    response = client.post("/api/v1/alerts/ai-verdict", json=payload, headers=AUTH)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["data"]["incident_id"] == "INC-TEST-9999"

    # Verificar que el GET subsiguiente retorna el nuevo dictamen
    get_res = client.get("/api/v1/alerts/ai-verdict", headers=AUTH)
    assert get_res.status_code == 200
    assert get_res.json()["incident_id"] == "INC-TEST-9999"
    assert get_res.json()["threat_level"] == "CRITICAL"
