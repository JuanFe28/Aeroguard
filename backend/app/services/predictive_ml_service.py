"""
AeroGuard — Servicio de Analítica Predictiva ML (CRISP-DM)

Ejecuta inferencia liviana en memoria (pure Python + NumPy, sin scikit-learn ni
statsmodels en la imagen de runtime) a partir de `predictive_models_artifact.json`:
- Random Forest compacto: clasificación de threat_level (LOW/MEDIUM/HIGH/CRITICAL)
- Regresión Lineal: puntaje continuo risk_score (0–100)
- Regresión Logística: probabilidad de alto riesgo / violación con umbral calibrado
- K-Means: asignación a perfil operativo de vuelo
- ARIMA: consulta de pronóstico diario de picos de incursiones (14 días)

Nota metodológica: todos los parámetros proceden del entrenamiento sintético CRISP-DM;
los resultados son recomendaciones académicas sujetas a revisión humana.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import numpy as np

ARTIFACT_PATH = Path(__file__).resolve().parent.parent / "data" / "predictive_models_artifact.json"


@lru_cache(maxsize=1)
def load_predictive_artifact() -> dict[str, Any]:
    """Carga y cachea el artefacto JSON de modelos predictivos."""
    if not ARTIFACT_PATH.exists():
        raise FileNotFoundError(
            f"Artefacto predictivo no encontrado en {ARTIFACT_PATH}. "
            "Ejecuta data_mining/05_predictive_models_benchmark.py."
        )
    with ARTIFACT_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _scale_numeric(features: list[str], means: list[float], scales: list[float], payload: Mapping[str, Any]) -> np.ndarray:
    vals = np.array([float(payload[name]) for name in features], dtype=float)
    mean_arr = np.asarray(means, dtype=float)
    scale_arr = np.where(np.asarray(scales, dtype=float) == 0.0, 1.0, np.asarray(scales, dtype=float))
    return (vals - mean_arr) / scale_arr


def _encode_linear_vector(prep: Mapping[str, Any], payload: Mapping[str, Any]) -> np.ndarray:
    num_vec = _scale_numeric(prep["numeric_features"], prep["scaler_mean"], prep["scaler_scale"], payload)
    cat_parts: list[float] = []
    for col, categories in zip(prep["categorical_features"], prep["categorical_categories"]):
        val = str(payload[col])
        for cat in categories:
            cat_parts.append(1.0 if val == cat else 0.0)
    return np.concatenate([num_vec, np.asarray(cat_parts, dtype=float)])


def _encode_tree_vector(rf_cfg: Mapping[str, Any], payload: Mapping[str, Any]) -> np.ndarray:
    num_vec = _scale_numeric(rf_cfg["numeric_features"], rf_cfg["scaler_mean"], rf_cfg["scaler_scale"], payload)
    cat_indices: list[float] = []
    for col, categories in zip(rf_cfg["categorical_features"], rf_cfg["categorical_categories"]):
        val = str(payload[col])
        try:
            idx = float(categories.index(val))
        except ValueError:
            idx = -1.0
        cat_indices.append(idx)
    return np.concatenate([num_vec, np.asarray(cat_indices, dtype=float)])


def _traverse_forest(x_vec: np.ndarray, rf_cfg: Mapping[str, Any]) -> tuple[str, dict[str, float]]:
    classes: list[str] = list(rf_cfg["classes"])
    trees: list[dict[str, Any]] = rf_cfg["trees"]
    avg_probs = np.zeros(len(classes), dtype=float)

    for tree in trees:
        node = 0
        cl = tree["children_left"]
        cr = tree["children_right"]
        feat = tree["feature"]
        thr = tree["threshold"]
        while cl[node] != -1:
            f_idx = feat[node]
            node = cl[node] if x_vec[f_idx] <= thr[node] else cr[node]
        avg_probs += np.asarray(tree["leaf_probs"][str(node)], dtype=float)

    avg_probs /= float(len(trees) or 1)
    best_idx = int(np.argmax(avg_probs))
    prob_map = {cls: round(float(avg_probs[i]), 4) for i, cls in enumerate(classes)}
    return classes[best_idx], prob_map


def _normalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "altitude_m": float(payload.get("altitude_m", 120.0)),
        "speed_ms": float(payload.get("speed_ms", 12.0)),
        "vertical_speed_ms": float(payload.get("vertical_speed_ms", 0.0)),
        "heading_deg": float(payload.get("heading_deg", 180.0)),
        "distance_to_zone_m": float(payload.get("distance_to_zone_m", 300.0)),
        "rf_signal_dbm": float(payload.get("rf_signal_dbm", -72.0)),
        "battery_est_pct": float(payload.get("battery_est_pct", 75.0)),
        "ai_confidence": float(payload.get("ai_confidence", 0.85)),
        "wind_speed_kmh": float(payload.get("wind_speed_kmh", 12.0)),
        "drone_class": str(payload.get("drone_class", "quadcopter")),
        "flight_pattern": str(payload.get("flight_pattern", "Directo")),
        "weather_condition": str(payload.get("weather_condition", "Despejado")),
        "city_zone": str(payload.get("city_zone", "Bucaramanga")),
    }


def _build_key_factors(norm: Mapping[str, Any], threat_level: str, profile_label: str) -> list[str]:
    factors = [
        f"Distancia al perímetro: {norm['distance_to_zone_m']:.1f} m",
        f"Altitud observada: {norm['altitude_m']:.1f} m ({'sobre cota 120 m' if norm['altitude_m'] > 120.0 else 'bajo cota 120 m'})",
        f"Velocidad horizontal: {norm['speed_ms']:.1f} m/s | Patrón: {norm['flight_pattern']}",
        f"Clase estimada: {norm['drone_class']} | Perfil K-Means: {profile_label}",
        f"Clasificación RF ({threat_level}): sujeta a verificación humana (modelo entrenado con datos sintéticos)",
    ]
    return factors


class PredictiveMLService:
    """Fachada para analítica predictiva multi-modelo en tiempo real y pronósticos ARIMA."""

    def evaluate_telemetry(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        art = load_predictive_artifact()
        norm = _normalize_payload(payload)

        # 1. Regresión Lineal + Logística (mismo preprocesador escalado + one-hot)
        x_lin = _encode_linear_vector(art["linear_logistic_preprocessor"], norm)
        lr_cfg = art["linear_regression"]
        raw_risk = float(np.dot(x_lin, np.asarray(lr_cfg["coef"], dtype=float)) + float(lr_cfg["intercept"]))
        risk_score = round(max(0.0, min(100.0, raw_risk)), 2)

        log_cfg = art["logistic_regression"]
        z = float(np.dot(x_lin, np.asarray(log_cfg["coef"], dtype=float)) + float(log_cfg["intercept"]))
        z_clamped = max(-60.0, min(60.0, z))
        breach_prob = round(1.0 / (1.0 + math.exp(-z_clamped)), 4)
        opt_thr = float(log_cfg["optimal_threshold"])
        high_risk_flag = breach_prob >= opt_thr

        # 2. Random Forest compacto en runtime
        rf_cfg = art["random_forest"]
        x_tree = _encode_tree_vector(rf_cfg, norm)
        threat_level, class_probs = _traverse_forest(x_tree, rf_cfg)
        rf_confidence = round(float(class_probs.get(threat_level, 0.0)), 4)

        # 3. K-Means (perfil operativo de vuelo)
        km_cfg = art["kmeans"]
        x_km = _scale_numeric(km_cfg["features"], km_cfg["scaler_mean"], km_cfg["scaler_scale"], norm)
        centroids = np.asarray(km_cfg["centroids_scaled"], dtype=float)
        dists = np.linalg.norm(centroids - x_km, axis=1)
        cluster_id = int(np.argmin(dists))
        profile = next(
            (p for p in km_cfg["profiles"] if int(p["cluster_id"]) == cluster_id),
            km_cfg["profiles"][0],
        )

        return {
            "threat_level": threat_level,
            "confidence": rf_confidence,
            "class_probabilities": class_probs,
            "risk_score": risk_score,
            "geofence_breach_probability": breach_prob,
            "high_risk_threshold": opt_thr,
            "high_risk_flag": high_risk_flag,
            "cluster_id": cluster_id,
            "flight_profile": profile["label"],
            "profile_description": profile["description"],
            "centroid_distance": round(float(dists[cluster_id]), 4),
            "key_factors": _build_key_factors(norm, threat_level, profile["label"]),
            "models_applied": ["RandomForest", "LinearRegression", "LogisticRegression", "KMeans"],
            "model_version": art["version"],
            "data_origin": art.get("data_origin", "synthetic_crisp_dm_dataset"),
            "simulation": True,
            "human_review_required": True,
        }

    def get_forecast(self) -> dict[str, Any]:
        art = load_predictive_artifact()
        arima = art["arima"]
        return {
            "model": arima["metrics"]["modelo"],
            "order": arima["metrics"]["order"],
            "metrics": arima["metrics"],
            "recent_history_30d": arima["recent_history_30d"],
            "forecast_14d": arima["forecast_14d"],
            "peak_forecast_14d": arima["metrics"]["peak_forecast_14d"],
            "data_origin": art.get("data_origin", "synthetic_crisp_dm_dataset"),
            "human_review_required": True,
        }

    def get_models_summary(self) -> dict[str, Any]:
        art = load_predictive_artifact()
        dt_block = art.get("decision_tree", {}).get("metrics", {})
        return {
            "version": art["version"],
            "generated_at_utc": art["generated_at_utc"],
            "data_origin": art.get("data_origin", "synthetic_crisp_dm_dataset"),
            "dataset_stats": art["dataset_stats"],
            "production_decision": art["production_decision"],
            "models": {
                "regresion_lineal": art["linear_regression"]["metrics"],
                "regresion_logistica": art["logistic_regression"]["metrics"],
                "kmeans": art["kmeans"]["metrics"],
                "arbol_decision": dt_block,
                "random_forest": art["random_forest"]["metrics"],
                "arima": art["arima"]["metrics"],
            },
        }


predictive_ml_service = PredictiveMLService()
