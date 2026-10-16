"""
AeroGuard — Tests para Endpoint de Visión Artificial (RF-021 / CODE-01)
Valida los criterios de aceptación Gherkin de HU-01:
- Escenario 1: Inferencia real en imagen válida JPEG/PNG con coordenadas de bounding_box.
- Escenario 2: Rechazo con HTTP 400 de archivo no soportado (.txt, etc.).
- Escenario 3: Rechazo con HTTP 400 de archivo vacío.
- Escenario 4: Control de acceso RBAC.
"""

import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.core.security import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


def _generate_test_image(format="JPEG", width=320, height=240, color=(135, 206, 235)) -> bytes:
    """Genera una imagen en memoria para testing (simulando cielo y objeto tipo dron)."""
    img = Image.new("RGB", (width, height), color=color)
    # Dibujar un recuadro oscuro simulando dron en el tercio superior
    for x in range(120, 190):
        for y in range(40, 90):
            img.putpixel((x, y), (10, 10, 10))
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return buffer.getvalue()


def test_ai_analyze_valid_jpeg_success(client: TestClient):
    """Escenario 1: Operador envía imagen JPEG válida y recibe detección real."""
    token = create_access_token({"sub": "operator_test", "role": "operator"})
    img_bytes = _generate_test_image("JPEG")

    files = {
        "file": ("drone_feed.jpg", img_bytes, "image/jpeg")
    }
    data = {
        "sensor_id": "CAM-BGA-NORTE-01"
    }

    response = client.post(
        "/api/v1/ai/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data,
    )

    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "success"
    assert res["sensor_id"] == "CAM-BGA-NORTE-01"
    assert "YOLO" in res["engine"] or "OpenCV" in res["engine"]
    assert "timestamp" in res
    assert res["processing_time_ms"] < 1500

    # Detección
    detection = res["detection"]
    assert isinstance(detection["is_drone"], bool)
    assert detection["is_drone"] is True
    assert 0.0 <= detection["confidence"] <= 1.0
    assert detection["label"] in ["quadcopter_uav", "no_drone_detected"]
    assert detection["threat_level"] in ["CRITICAL", "HIGH", "LOW"]

    # Bounding Box
    bb = detection["bounding_box"]
    assert "x_min" in bb and "y_min" in bb and "width" in bb and "height" in bb
    assert bb["width"] > 0 and bb["height"] > 0


def test_ai_analyze_invalid_file_type_rejected(client: TestClient):
    """Escenario 2: Archivo no imagen (.txt) es rechazado con HTTP 400 y mensaje de error."""
    token = create_access_token({"sub": "operator_test", "role": "operator"})
    invalid_bytes = b"Este es un archivo de texto no permitido."

    files = {
        "file": ("documento.txt", invalid_bytes, "text/plain")
    }

    response = client.post(
        "/api/v1/ai/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
    )

    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert "Formato de archivo inválido" in detail
    assert "JPEG, PNG, WEBP" in detail


def test_ai_analyze_empty_file_rejected(client: TestClient):
    """Escenario 3: Archivo vacío es rechazado con HTTP 400."""
    token = create_access_token({"sub": "operator_test", "role": "operator"})

    files = {
        "file": ("empty.jpg", b"", "image/jpeg")
    }

    response = client.post(
        "/api/v1/ai/analyze",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
    )

    assert response.status_code == 400
    detail = response.json().get("detail", "")
    assert "vacío" in detail.lower()


def test_ai_analyze_unauthorized_access(client: TestClient):
    """Escenario 4: Petición sin token JWT es rechazada con HTTP 401."""
    img_bytes = _generate_test_image("PNG")
    files = {
        "file": ("frame.png", img_bytes, "image/png")
    }

    response = client.post(
        "/api/v1/ai/analyze",
        files=files,
    )

    assert response.status_code == 401
