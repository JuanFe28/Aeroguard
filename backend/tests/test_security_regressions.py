"""Regresiones de seguridad verificadas durante TEST-03."""

from datetime import datetime, timezone
from pathlib import Path
import socket

from fastapi import HTTPException
from fastapi.websockets import WebSocketDisconnect
import pytest

from app.api.v1.endpoints import alerts, reports, websocket
from app.core.config import Settings, settings
from app.core.security import create_access_token, create_refresh_token, create_reset_token, decode_token
from app.models.models import User, UserRole
from app.services import audit_service, user_service
from scripts import expo_local


def test_default_reports_directory_is_private_to_current_user(monkeypatch, tmp_path):
    monkeypatch.delenv("REPORTS_DIR", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    configured = Settings(_env_file=None)
    assert configured.REPORTS_DIR == str(tmp_path / ".aeroguard" / "reports")


def test_reports_created_in_same_second_do_not_overwrite(monkeypatch, tmp_path, isolated_client):
    monkeypatch.setattr(settings, "REPORTS_DIR", str(tmp_path))
    fixed_now = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)

    class FixedDatetime:
        @staticmethod
        def now(tz=None):
            return fixed_now

    monkeypatch.setattr(reports, "datetime", FixedDatetime)
    token = create_access_token({"sub": "admin", "role": "admin"})
    for _ in range(2):
        response = isolated_client.post(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "Prueba de colisión de reportes", "type": "summary", "format": "pdf"},
        )
        assert response.status_code == 201, response.text
    files = list(tmp_path.glob("*.pdf"))
    assert len(files) == 2, "Dos reportes creados en el mismo segundo sobrescriben el archivo"
    assert all(path.read_bytes().startswith(b"%PDF-") for path in files)


@pytest.mark.parametrize("environment,debug", [("production", True), ("staging", True), ("development", False)])
def test_unsigned_demo_token_rejected_outside_local_debug(monkeypatch, environment, debug):
    monkeypatch.setattr(settings, "APP_ENV", environment)
    monkeypatch.setattr(settings, "DEBUG", debug)
    with pytest.raises(HTTPException) as rejected:
        decode_token("mock_token_admin")
    assert rejected.value.status_code == 401


def test_local_debug_demo_token_remains_supported(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEBUG", True)
    assert decode_token("mock_token_admin")["sub"] == "admin"


def test_production_http_rejects_unsigned_demo_token(monkeypatch, isolated_client):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    response = isolated_client.get("/api/v1/users", headers={"Authorization": "Bearer mock_token_admin"})
    assert response.status_code == 401


def test_production_websocket_rejects_unsigned_demo_token(monkeypatch, isolated_client):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    with pytest.raises(WebSocketDisconnect) as rejected:
        with isolated_client.websocket_connect("/ws/live?token=mock_token_admin") as ws:
            ws.receive_json()
    assert rejected.value.code == 4001


@pytest.mark.parametrize("token_kind", ["refresh", "reset", "missing_subject"])
def test_websocket_requires_access_token_and_subject(token_kind, isolated_client):
    if token_kind == "refresh":
        token = create_refresh_token({"sub": "admin", "role": "admin"})
    elif token_kind == "reset":
        token = create_reset_token("admin@aeroguard.co")
    else:
        token = create_access_token({"role": "admin"})
    with pytest.raises(WebSocketDisconnect) as rejected:
        with isolated_client.websocket_connect(f"/ws/live?token={token}") as ws:
            ws.receive_json()
    assert rejected.value.code == 4001


def test_production_real_jwt_still_authorizes_http_and_websocket(monkeypatch, isolated_client):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "DEBUG", False)
    token = create_access_token({"sub": "admin", "role": "admin"})
    response = isolated_client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    with isolated_client.websocket_connect(f"/ws/live?token={token}") as ws:
        assert ws.receive_json()["type"] == "connected"
        ws.send_json({"type": "ping", "data": {"timestamp": 123}})
        assert ws.receive_json()["data"]["client_timestamp"] == 123


def test_production_does_not_invent_deleted_users(monkeypatch, isolated_client):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    token = create_access_token({"sub": "deleted-user", "role": "admin"})
    response = isolated_client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_production_database_failure_does_not_grant_access(monkeypatch, isolated_client):
    monkeypatch.setattr(settings, "APP_ENV", "production")

    async def unavailable(*args, **kwargs):
        raise RuntimeError("Base de datos no disponible durante la prueba")

    monkeypatch.setattr(user_service, "get_user_by_username", unavailable)
    token = create_access_token({"sub": "admin", "role": "admin"})
    response = isolated_client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize("url", ["http://example.invalid/", "https://127.0.0.1:8000/health"])
def test_launcher_rejects_unsupported_targets_before_opening_a_connection(monkeypatch, url):
    def forbid_connection(*args, **kwargs):
        raise AssertionError("El comprobador intentó conectar con un destino no permitido")

    monkeypatch.setattr(socket, "create_connection", forbid_connection)
    assert expo_local.ready(url, b"healthy") is False


@pytest.mark.parametrize("account", ["missing", "disabled"])
def test_production_websocket_rejects_unavailable_accounts(monkeypatch, isolated_client, account):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    subject = "deleted-user" if account == "missing" else "admin"
    if account == "disabled":
        async def disabled_user(*args, **kwargs):
            return User(username="admin", role=UserRole.ADMIN, is_active=False)

        monkeypatch.setattr(user_service, "get_user_by_username", disabled_user)
    token = create_access_token({"sub": subject, "role": "admin"})
    with pytest.raises(WebSocketDisconnect) as rejected:
        with isolated_client.websocket_connect(f"/ws/live?token={token}") as ws:
            ws.receive_json()
    assert rejected.value.code == 4001


@pytest.mark.parametrize("account,expected_status", [("active", 200), ("missing", 401), ("disabled", 403)])
def test_production_refresh_requires_active_account(monkeypatch, isolated_client, account, expected_status):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    subject = "deleted-user" if account == "missing" else "admin"
    if account == "disabled":
        async def disabled_user(*args, **kwargs):
            return User(username="admin", role=UserRole.ADMIN, is_active=False)

        monkeypatch.setattr(user_service, "get_user_by_username", disabled_user)
    token = create_refresh_token({"sub": subject, "role": "admin"})
    response = isolated_client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert response.status_code == expected_status
    if expected_status == 200:
        assert decode_token(response.json()["access_token"])["type"] == "access"


def test_failed_login_keeps_401_when_audit_is_unavailable(monkeypatch, isolated_client):
    async def unavailable(*args, **kwargs):
        raise RuntimeError("Auditoría no disponible durante la prueba")

    monkeypatch.setattr(audit_service, "log_audit", unavailable)
    response = isolated_client.post("/api/v1/auth/token", data={"username": "invalid-user", "password": "bad"})
    assert response.status_code == 401


def test_verdict_still_returns_success_when_broadcast_fails(monkeypatch, isolated_client):
    async def unavailable(*args, **kwargs):
        raise RuntimeError("Broadcast no disponible durante la prueba")

    monkeypatch.setattr(websocket.manager, "broadcast", unavailable)
    monkeypatch.setattr(alerts, "_latest_verdict", dict(alerts._latest_verdict))
    response = isolated_client.post("/api/v1/alerts/ai-verdict", json={
        "incident_id": "TEST-03-BROADCAST", "ai_verdict": "Dictamen de prueba",
        "threat_level": "LOW", "drone_id": "TEST-03",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"
