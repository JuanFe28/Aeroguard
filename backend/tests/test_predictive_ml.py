"""Pruebas unitarias e HTTP para la analítica predictiva multi-modelo (CRISP-DM)."""

import math
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.services.predictive_ml_service import load_predictive_artifact, predictive_ml_service

AUTH = {"Authorization": "Bearer " + create_access_token({"sub": "admin", "role": "admin"})}


def test_predictive_artifact_integrity():
    load_predictive_artifact.cache_clear()
    art = load_predictive_artifact()
    assert art["dataset_stats"]["clean_records"] >= 105000
    assert len(art["random_forest"]["trees"]) == 12
    assert len(art["kmeans"]["profiles"]) == 4
    assert len(art["arima"]["forecast_14d"]) == 14
    assert "metrics" in art["decision_tree"]


def test_service_inference_bird_vs_critical_intrusion():
    low_contact = predictive_ml_service.evaluate_telemetry(
        {
            "altitude_m": 45.0,
            "speed_ms": 5.0,
            "distance_to_zone_m": 1600.0,
            "rf_signal_dbm": -95.0,
            "ai_confidence": 0.65,
            "drone_class": "bird_false_pos",
            "flight_pattern": "Estacionario",
        }
    )
    critical_contact = predictive_ml_service.evaluate_telemetry(
        {
            "altitude_m": 195.0,
            "speed_ms": 28.0,
            "distance_to_zone_m": 60.0,
            "rf_signal_dbm": -40.0,
            "ai_confidence": 0.95,
            "drone_class": "diy_custom",
            "flight_pattern": "Evasivo",
        }
    )

    assert low_contact["threat_level"] == "LOW"
    assert critical_contact["threat_level"] in {"HIGH", "CRITICAL"}
    assert critical_contact["risk_score"] > low_contact["risk_score"]
    assert critical_contact["geofence_breach_probability"] > low_contact["geofence_breach_probability"]
    assert abs(sum(critical_contact["class_probabilities"].values()) - 1.0) < 0.02
    assert 0.0 <= critical_contact["risk_score"] <= 100.0
    assert 0.0 <= critical_contact["geofence_breach_probability"] <= 1.0
    assert math.isfinite(critical_contact["centroid_distance"])
    assert critical_contact["human_review_required"] is True
    assert critical_contact["simulation"] is True


def test_predictions_endpoints_require_auth_and_validate_inputs(isolated_client: TestClient):
    unauth = isolated_client.get("/api/v1/predictions/summary")
    assert unauth.status_code == 401

    invalid = isolated_client.post(
        "/api/v1/predictions/evaluate",
        json={"altitude_m": 5000.0, "speed_ms": 10.0, "distance_to_zone_m": 200.0},
        headers=AUTH,
    )
    assert invalid.status_code == 422

    nan_raw = isolated_client.post(
        "/api/v1/predictions/evaluate",
        content='{"altitude_m": NaN, "speed_ms": 10.0, "distance_to_zone_m": 200.0}',
        headers={**AUTH, "Content-Type": "application/json"},
    )
    assert nan_raw.status_code == 422


def test_predictions_endpoints_summary_forecast_and_no_side_effects(isolated_client: TestClient):
    alerts_before = isolated_client.get("/api/v1/alerts", headers=AUTH).json()
    verdict_before = isolated_client.get("/api/v1/alerts/ai-verdict", headers=AUTH).json()

    summary_res = isolated_client.get("/api/v1/predictions/summary", headers=AUTH)
    assert summary_res.status_code == 200
    summary_data = summary_res.json()["data"]
    assert set(summary_data["models"].keys()) == {
        "regresion_lineal",
        "regresion_logistica",
        "kmeans",
        "arbol_decision",
        "random_forest",
        "arima",
    }

    forecast_res = isolated_client.get("/api/v1/predictions/forecast", headers=AUTH)
    assert forecast_res.status_code == 200
    forecast_data = forecast_res.json()["data"]
    assert len(forecast_data["forecast_14d"]) == 14
    assert len(forecast_data["recent_history_30d"]) == 30
    assert forecast_data["peak_forecast_14d"]["predicted_high_risk"] > 0

    eval_res = isolated_client.post(
        "/api/v1/predictions/evaluate",
        json={
            "drone_id": "UAV-PRED-01",
            "altitude_m": 150.0,
            "speed_ms": 22.0,
            "distance_to_zone_m": 95.0,
            "drone_class": "fixed_wing",
            "flight_pattern": "Directo",
        },
        headers=AUTH,
    )
    assert eval_res.status_code == 200
    eval_body = eval_res.json()
    assert eval_body["simulation"] is True
    assert eval_body["data"]["threat_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert eval_body["data"]["cluster_id"] in {0, 1, 2, 3}

    alerts_after = isolated_client.get("/api/v1/alerts", headers=AUTH).json()
    verdict_after = isolated_client.get("/api/v1/alerts/ai-verdict", headers=AUTH).json()
    assert alerts_after == alerts_before
    assert verdict_after == verdict_before
