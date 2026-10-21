"""Regresiones de la auditoría de Release; no validan precisión de drones reales."""

import io
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.security import create_access_token
from app.models.models import AuditLog, Base
from app.services.ai_vision_service import AIVisionService
from app.services.audit_service import log_audit, verify_audit_chain


def headers(role="operator"):
    return {"Authorization": "Bearer " + create_access_token({"sub": "release_probe", "role": role})}


@pytest.mark.parametrize("method,path,payload", [
    ("GET", "/api/v1/alerts/ai-verdict", None),
    ("POST", "/api/v1/alerts/ai-verdict", {"incident_id": "probe", "ai_verdict": "probe"}),
    ("POST", "/api/v1/alerts/trigger-incident", {}),
    ("POST", "/api/v1/sensors/telemetry", {
        "sensor_id": "probe", "latitude": 0, "longitude": 0,
        "altitude": 10, "speed": 1, "heading": 0,
    }),
])
def test_operational_endpoints_require_authentication(isolated_client, method, path, payload):
    response = isolated_client.request(method, path, json=payload)
    assert response.status_code == 401


def test_analyst_cannot_inject_verdict(isolated_client):
    response = isolated_client.post("/api/v1/alerts/ai-verdict", headers=headers("analyst"),
                                    json={"incident_id": "probe", "ai_verdict": "probe"})
    assert response.status_code == 403


def test_corrupt_image_is_rejected(isolated_client):
    response = isolated_client.post("/api/v1/ai/analyze", headers=headers(),
                                    files={"file": ("fake.jpg", b"not an image", "image/jpeg")})
    assert response.status_code == 400


def test_oversized_image_is_rejected_before_decoding(isolated_client):
    response = isolated_client.post("/api/v1/ai/analyze", headers=headers(),
                                    files={"file": ("large.jpg", b"x" * (10 * 1024 * 1024 + 1), "image/jpeg")})
    assert response.status_code == 413


def test_disguised_gif_is_rejected(isolated_client):
    data = io.BytesIO()
    Image.new("RGB", (16, 16), "white").save(data, format="GIF")
    response = isolated_client.post("/api/v1/ai/analyze", headers=headers(),
                                    files={"file": ("fake.jpg", data.getvalue(), "image/jpeg")})
    assert response.status_code == 400


def test_pillow_fallback_identifies_actual_engine():
    image = io.BytesIO()
    Image.new("RGB", (64, 64), "white").save(image, format="PNG")
    service = AIVisionService()
    service.detector = None
    result = service.analyze_image_bytes(image.getvalue())
    assert result["engine"] == "Pillow-Heuristic"
    assert result["model_validated"] is False


@pytest.mark.parametrize("class_name,expected", [("person", False), ("airplane", False), ("drone", True)])
def test_yolo_only_accepts_explicit_drone_classes(class_name, expected):
    from detector import YOLODetector

    box = SimpleNamespace(cls=[0], conf=[0.99], xyxy=np.array([[1, 2, 30, 40]]))
    result = SimpleNamespace(boxes=[box], names={0: class_name})
    service = YOLODetector("test-only.pt")
    service._loaded = True
    service._model = lambda *args, **kwargs: [result]
    assert service.analyze(np.zeros((48, 48, 3), dtype=np.uint8)).is_drone is expected


@pytest.mark.asyncio
async def test_audit_chain_verifies_new_records_and_detects_tampering():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            await log_audit(db, action="READ", resource="release", username="probe")
            await log_audit(db, action="EXPORT", resource="release", username="probe")
            assert (await verify_audit_chain(db))["valid"] is True
            records = (await db.execute(select(AuditLog).order_by(AuditLog.timestamp))).scalars().all()
            records[0].action = "TAMPERED"
            await db.commit()
            assert (await verify_audit_chain(db))["valid"] is False
    finally:
        await engine.dispose()


def test_telemetry_does_not_claim_visual_inference(isolated_client):
    response = isolated_client.post("/api/v1/sensors/telemetry", headers=headers(), json={
        "sensor_id": "probe", "latitude": 0, "longitude": 0,
        "altitude": 10, "speed": 1, "heading": 0,
    })
    assert response.status_code == 202
    detection = isolated_client.get("/api/v1/detections/" + response.json()["detection_id"],
                                    headers=headers()).json()
    assert detection["ai_analyzed"] is False
    assert detection["ai_confidence"] is None
    assert detection["is_drone"] is False


def test_report_exports_identify_database_source(isolated_client):
    response = isolated_client.get("/api/v1/reports/export/excel", headers=headers("analyst"))
    assert response.status_code == 200
    assert response.headers.get("X-AeroGuard-Data-Source") == "database"
    from openpyxl import load_workbook
    workbook = load_workbook(io.BytesIO(response.content))
    try:
        assert "DEMO" not in workbook["Telemetría e Incursiones"]["A1"].value
    finally:
        workbook.close()
