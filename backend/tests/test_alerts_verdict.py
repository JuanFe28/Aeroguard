"""
Tests para endpoints de Dictamen Táctico de IA (HU-03 / [CODE-03])
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)
AUTH = {"Authorization": "Bearer " + create_access_token({"sub": "admin", "role": "admin"})}


def test_get_ai_verdict_success(monkeypatch):
    """Valida obtención del dictamen táctico de IA actual."""
    from app.api.v1.endpoints import alerts
    monkeypatch.setattr(alerts, '_latest_verdict', {
        'incident_id': None, 'timestamp': None, 'ai_verdict': 'Sin dictámenes registrados.',
        'threat_level': None, 'drone_id': None,
    })
    response = client.get("/api/v1/alerts/ai-verdict", headers=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert "incident_id" in data
    assert "ai_verdict" in data
    assert "threat_level" in data
    assert "drone_id" in data
    assert data['incident_id'] is None
    assert data['threat_level'] is None
    assert data['drone_id'] is None
    assert data['timestamp'] is None


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
