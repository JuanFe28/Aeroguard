"""
Tests de Autenticación y RBAC (Role-Based Access Control)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)


def test_login_success():
    """Prueba que el login devuelve 401 para credenciales incorrectas."""
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales incorrectas."


def test_access_denied_without_token():
    """Prueba que los endpoints protegidos devuelven 401 si no hay token."""
    response = client.get("/api/v1/users")
    assert response.status_code == 401
    assert "No authenticated" in response.json().get("detail", "") or "Not authenticated" in response.json().get("detail", "")


def test_rbac_operator_cannot_access_users():
    """Prueba RBAC: un operador no puede listar usuarios."""
    token = create_access_token({"sub": "operator_user", "role": "operator"})
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert "No tienes permiso para" in response.json().get("detail", "")


def test_rbac_analyst_cannot_access_users():
    """Prueba RBAC: un analista no puede administrar usuarios."""
    token = create_access_token({"sub": "analyst_user", "role": "analyst"})
    response = client.post(
        "/api/v1/users",
        json={"username": "test", "email": "test@test.com", "password": "TestPassword1!", "first_name": "T", "last_name": "T"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_rbac_analyst_cannot_create_zones():
    """Prueba RBAC: un analista no puede crear zonas."""
    token = create_access_token({"sub": "analyst_user", "role": "analyst"})
    response = client.post(
        "/api/v1/zones",
        json={"name": "Test Zone", "threat_level": "low"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_rbac_analyst_can_view_history():
    """Prueba RBAC: un analista puede consultar historial."""
    token = create_access_token({"sub": "analyst_user", "role": "analyst"})
    response = client.get(
        "/api/v1/history",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code != 403


def test_rbac_analyst_can_generate_reports():
    """Prueba RBAC: un analista puede generar reportes."""
    token = create_access_token({"sub": "analyst_user", "role": "analyst"})
    response = client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code != 403
