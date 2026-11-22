"""
AeroGuard - Exportacion de datos para Orange Data Mining.

Genera dos archivos en data_mining/orange/ con el encabezado de una fila de Orange
("<banderas><tipo>#nombre"), limpios con las mismas reglas del pipeline (limpieza.py):

  aeroguard_entrenamiento.csv.gz  <- data/aeroguard_raw_telemetry.csv     (dataset principal)
  aeroguard_prueba_lote2.csv.gz   <- data/aeroguard_lote_adicional_120000.csv (lote independiente)

Al abrirlos con el widget File de Orange:
  - threat_level queda como variable objetivo (clase),
  - las 13 variables del pipeline quedan como atributos,
  - identificadores y coordenadas quedan como metadatos (no entran al modelo).

Uso:  python data_mining/03_export_orange.py
"""

import json
import os
import sys

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from limpieza import clean_telemetry, compute_risk_score  # noqa: E402

DATA_DIR = os.path.join(BASE_DIR, "data")
ORANGE_DIR = os.path.join(BASE_DIR, "orange")

SOURCES = [
    ("aeroguard_raw_telemetry.csv", "aeroguard_entrenamiento.csv.gz"),
    ("aeroguard_lote_adicional_120000.csv", "aeroguard_prueba_lote2.csv.gz"),
]
REGRESSION_TARGET_GZ = "aeroguard_regresion_riesgo.csv.gz"

# Mismas variables que usa el pipeline de scikit-learn (Fase 4).
NUMERIC = [
    "altitude_m", "speed_ms", "vertical_speed_ms", "heading_deg",
    "distance_to_zone_m", "rf_signal_dbm", "battery_est_pct",
    "ai_confidence", "wind_speed_kmh",
]
CATEGORICAL = ["drone_class", "flight_pattern", "weather_condition", "city_zone"]
TARGET = "threat_level"
META = ["record_id", "timestamp", "drone_id", "sensor_id", "latitude", "longitude"]


def orange_header(col):
    if col in META:
        return f"m{'C' if col in ('latitude', 'longitude') else 'S'}#{col}"
    if col in NUMERIC:
        return f"C#{col}"
    if col in CATEGORICAL:
        return f"D#{col}"
    return f"cD#{col}"  # TARGET


def export(source_name, target_name):
    source = os.path.join(DATA_DIR, source_name)
    if not os.path.exists(source):
        hint = " Ejecuta antes 01_generate_dataset.py." if source_name.startswith("aeroguard_raw") else ""
        sys.exit(f"No existe {source}.{hint}")

    df_clean, summary = clean_telemetry(pd.read_csv(source, low_memory=False))
    out = df_clean[META + NUMERIC + CATEGORICAL + [TARGET]].sort_values("record_id")
    out = out.rename(columns={c: orange_header(c) for c in out.columns})

    os.makedirs(ORANGE_DIR, exist_ok=True)
    target = os.path.join(ORANGE_DIR, target_name)
    out.to_csv(target, index=False)
    summary["distribucion_threat_level"] = df_clean[TARGET].value_counts().to_dict()
    print(f"{target_name}: {summary['registros_brutos']:,} brutos -> {summary['registros_limpios']:,} limpios")
    return target_name, summary


def export_regression_risk(source_name="aeroguard_raw_telemetry.csv", target_name=REGRESSION_TARGET_GZ):
    """Exporta dataset limpio con variable continua risk_score (cC#) para Regresion Lineal en Orange."""
    source = os.path.join(DATA_DIR, source_name)
    if not os.path.exists(source):
        sys.exit(f"No existe {source}. Ejecuta antes 01_generate_dataset.py.")

    df_clean, summary = clean_telemetry(pd.read_csv(source, low_memory=False))
    df_clean["risk_score"] = compute_risk_score(df_clean, seed=42)

    cols = META + ["threat_level"] + NUMERIC + CATEGORICAL + ["risk_score"]
    out = df_clean[cols].sort_values("record_id")
    rename_map = {c: orange_header(c) for c in META + NUMERIC + CATEGORICAL}
    rename_map["threat_level"] = "mS#threat_level"  # metadato para evitar data leakage en regresion
    rename_map["risk_score"] = "cC#risk_score"       # variable objetivo continua
    out = out.rename(columns=rename_map)

    os.makedirs(ORANGE_DIR, exist_ok=True)
    target = os.path.join(ORANGE_DIR, target_name)
    out.to_csv(target, index=False)
    summary["risk_score_mean"] = round(float(df_clean["risk_score"].mean()), 2)
    summary["risk_score_std"] = round(float(df_clean["risk_score"].std()), 2)
    print(f"{target_name}: {summary['registros_brutos']:,} brutos -> {summary['registros_limpios']:,} limpios (risk_score cC#)")
    return target_name, summary


def main():
    report = dict(export(src, dst) for src, dst in SOURCES)
    reg_name, reg_summary = export_regression_risk()
    report[reg_name] = reg_summary
    with open(os.path.join(ORANGE_DIR, "resumen_limpieza.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"Resumen: {os.path.join(ORANGE_DIR, 'resumen_limpieza.json')}")


if __name__ == "__main__":
    main()
