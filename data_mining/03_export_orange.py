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
from limpieza import clean_telemetry  # noqa: E402

DATA_DIR = os.path.join(BASE_DIR, "data")
ORANGE_DIR = os.path.join(BASE_DIR, "orange")

SOURCES = [
    ("aeroguard_raw_telemetry.csv", "aeroguard_entrenamiento.csv.gz"),
    ("aeroguard_lote_adicional_120000.csv", "aeroguard_prueba_lote2.csv.gz"),
]

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


def main():
    report = dict(export(src, dst) for src, dst in SOURCES)
    with open(os.path.join(ORANGE_DIR, "resumen_limpieza.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"Resumen: {os.path.join(ORANGE_DIR, 'resumen_limpieza.json')}")


if __name__ == "__main__":
    main()
