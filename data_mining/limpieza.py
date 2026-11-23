"""
AeroGuard - Reglas de limpieza compartidas (CRISP-DM Fase 3).

Las usan 02_crisp_dm_pipeline.py y 03_export_orange.py para que el dataset
principal y los lotes adicionales se limpien exactamente igual.
"""

import numpy as np
import pandas as pd

CORRUPT_TOKENS = ["SENSOR_ERR", "???", "CORRUPTED_HEX_0xFF"]

NUMERIC_COLS = [
    "latitude", "longitude", "altitude_m", "speed_ms", "vertical_speed_ms",
    "heading_deg", "distance_to_zone_m", "rf_signal_dbm", "battery_est_pct",
    "ai_confidence", "wind_speed_kmh",
]

CATEGORICAL_COLS = ["weather_condition", "drone_class", "flight_pattern", "city_zone", "sensor_id"]

# Rango valido de las variables acotadas: fuera de el, el valor se vuelve nulo.
BOUNDED = {"ai_confidence": (0.0, 1.0), "battery_est_pct": (0.0, 100.0), "heading_deg": (0.0, 360.0)}

# Limites fisicos: la fila se descarta si el valor esta fuera (anomalias extremas inyectadas).
PHYSICAL_LIMITS = {
    "altitude_m": (0.0, 1500.0),
    "speed_ms": (0.0, 100.0),
    "distance_to_zone_m": (0.0, 25000.0),
    "wind_speed_kmh": (0.0, 120.0),
}


def clean_telemetry(df_raw):
    """Devuelve (df_limpio, resumen) aplicando deduplicacion, coercion, rangos, filtro e imputacion."""
    summary = {"registros_brutos": int(len(df_raw))}

    # 1. Duplicados exactos
    df = df_raw.drop_duplicates().copy()
    summary["duplicados_eliminados"] = int(len(df_raw) - len(df))

    # 2. Tokens corruptos -> NaN
    summary["celdas_corruptas"] = int(df.isin(CORRUPT_TOKENS).sum().sum())
    df = df.replace(CORRUPT_TOKENS, np.nan)

    # 3. Conversion numerica segura
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Rangos imposibles en variables acotadas -> NaN
    for col, (low, high) in BOUNDED.items():
        df.loc[(df[col] < low) | (df[col] > high), col] = np.nan

    # 5. Filtro de anomalias fisicas extremas
    valid = pd.Series(True, index=df.index)
    for col, (low, high) in PHYSICAL_LIMITS.items():
        valid &= df[col].isna() | ((df[col] >= low) & (df[col] <= high))
    summary["filas_fuera_de_rango_fisico"] = int((~valid).sum())
    df = df[valid].copy()

    # 6. Imputacion: mediana (numericas) y moda (categoricas)
    summary["nulos_imputados"] = int(df[NUMERIC_COLS + CATEGORICAL_COLS].isna().sum().sum())
    for col in NUMERIC_COLS:
        if df[col].isna().any():
            df[col] = df[col].fillna(df[col].median())
    for col in CATEGORICAL_COLS:
        if df[col].isna().any():
            df[col] = df[col].fillna(df[col].mode()[0])

    summary["registros_limpios"] = int(len(df))
    return df, summary


def compute_risk_score(df: pd.DataFrame, seed: int = 42) -> np.ndarray:
    """Calcula un puntaje continuo y reproducible de riesgo cinematico (0-100) sin usar threat_level."""
    class_base = {
        "bird_false_pos": 4.0,
        "quadcopter": 18.0,
        "hexacopter": 24.0,
        "fixed_wing": 30.0,
        "diy_custom": 35.0,
    }
    pattern_score = {
        "Estacionario": 2.0,
        "Erratico": 7.0,
        "Patrullaje": 10.0,
        "Directo": 15.0,
        "Evasivo": 19.0,
    }

    base = df["drone_class"].astype(str).map(class_base).fillna(18.0).to_numpy(dtype=float)
    pat = df["flight_pattern"].astype(str).map(pattern_score).fillna(6.0).to_numpy(dtype=float)
    dist = df["distance_to_zone_m"].to_numpy(dtype=float)
    alt = df["altitude_m"].to_numpy(dtype=float)
    spd = df["speed_ms"].to_numpy(dtype=float)
    rf = df["rf_signal_dbm"].to_numpy(dtype=float)
    conf = df["ai_confidence"].to_numpy(dtype=float)

    prox_component = 36.0 * np.exp(-np.clip(dist, 0.0, None) / 480.0)
    alt_component = np.clip((alt - 120.0) * 0.12, 0.0, 14.0) + 0.015 * np.clip(alt, 0.0, 350.0)
    spd_component = 0.48 * np.clip(spd, 0.0, 40.0)
    rf_component = np.clip((rf + 110.0) * 0.14, 0.0, 11.0)
    conf_component = np.clip(conf, 0.0, 1.0) * 4.5

    raw_score = base + pat + prox_component + alt_component + spd_component + rf_component + conf_component
    is_bird = (df["drone_class"].astype(str) == "bird_false_pos").to_numpy()
    raw_score = np.where(is_bird, 6.0 + 0.05 * spd + 2.0 * conf, raw_score)

    rng = np.random.default_rng(seed)
    noisy_score = raw_score + rng.normal(0.0, 2.5, size=len(df))
    return np.round(np.clip(noisy_score, 0.0, 100.0), 2)

