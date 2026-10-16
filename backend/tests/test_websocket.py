"""
Tests para WebSocket Endpoint y Heartbeat Táctico (HU-03 / [CODE-04])
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.api.v1.endpoints.websocket import broadcast_detection, broadcast_alert

client = TestClient(app)


def test_websocket_invalid_token_rejected():
    """Valida que una conexión con token inválido sea rechazada."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/live?token=invalid_token") as ws:
            ws.receive_json()


def test_websocket_connect_and_heartbeat_ping_pong():
    """Valida la conexión exitosa y el ciclo de vida del heartbeat ping-pong con RTT."""
    token = create_access_token({"sub": "operator_ws_test", "role": "operator"})
    with client.websocket_connect(f"/ws/live?token={token}") as ws:
        # 1. Recibir mensaje de bienvenida
        welcome = ws.receive_json()
        assert welcome["type"] == "connected"
        assert welcome["data"]["user"] == "operator_ws_test"
        assert "heartbeat_interval_s" in welcome["data"]

        # 2. Enviar Ping con timestamp de cliente
        client_ts = 1700000000123
        ws.send_json({"type": "ping", "data": {"timestamp": client_ts}})

        # 3. Recibir Pong con client_timestamp intacto para cálculo de RTT
        pong = ws.receive_json()
        assert pong["type"] == "pong"
        assert pong["data"]["client_timestamp"] == client_ts
        assert "server_timestamp" in pong["data"]


def test_websocket_broadcast_detection_and_alert():
    """Valida que los broadcasts del sistema lleguen a los clientes conectados."""
    token = create_access_token({"sub": "operator_ws_broadcast", "role": "operator"})
    with client.websocket_connect(f"/ws/live?token={token}") as ws:
        # Consumir bienvenida
        _ = ws.receive_json()

        # Simular broadcast de detección
        import asyncio
        det_data = {
            "id": "DET-WS-001",
            "drone_id": "UAV-402",
            "altitude": 145.0,
            "status": "active"
        }
        asyncio.run(broadcast_detection(det_data))

        # Verificar recepción en el cliente
        msg = ws.receive_json()
        assert msg["type"] == "detection_new"
        assert msg["data"]["id"] == "DET-WS-001"
        assert msg["data"]["altitude"] == 145.0
