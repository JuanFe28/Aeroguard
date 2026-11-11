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
