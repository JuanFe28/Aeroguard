#!/usr/bin/env python3
"""
AeroGuard C-UAS — Generador de Dataset Sintetico de Telemetria (CRISP-DM Fase 2)
Genera 125,000 registros con 20 columnas aplicando las reglas de distribucion:
- 80% Datos limpios con correlacion fisica y tactica real
- 10% Outliers extremos (fisicamente imposibles)
- 10% Datos sucios (nulos, valores corruptos/imposibles y filas duplicadas)
"""

import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

def generate_aeroguard_dataset(total_records=125000, random_seed=42):
    print("=" * 70)
    print(" [AEROGUARD C-UAS] Generacion de Telemetria de Drones (CRISP-DM)")
    print(f" Registros objetivo: {total_records:,} | Semilla: {random_seed}")
    print("=" * 70)

    np.random.seed(random_seed)

    # Carpetas destino
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, "aeroguard_raw_telemetry.csv")

    # Catalogos y valores nominales
    sensors_bga = ["CAM-BGA-NORTE-01", "RAD-BGA-SUR-02", "OPT-BGA-UTS-01"]
    sensors_bog = ["CAM-BOG-CENTRO-01", "RF-BOG-OESTE-03"]
    all_sensors = sensors_bga + sensors_bog

    drone_ids = [f"UAV-HK-{i:03d}" for i in range(101, 250)] + [f"UAV-COL-{i:03d}" for i in range(301, 450)]
    drone_classes = ["quadcopter", "fixed_wing", "hexacopter", "diy_custom", "bird_false_pos"]
    drone_class_weights = [0.45, 0.20, 0.15, 0.12, 0.08]

    weather_conditions = ["Despejado", "Nublado", "Lluvia", "Niebla"]
    weather_weights = [0.50, 0.30, 0.12, 0.08]

    flight_patterns = ["Directo", "Erratico", "Estacionario", "Patrullaje", "Evasivo"]
    pattern_weights = [0.28, 0.18, 0.14, 0.22, 0.18]

    # Distribucion del volumen
    num_outliers = int(total_records * 0.10)       # 12,500
    num_dirty = int(total_records * 0.10)          # 12,500
    num_clean = total_records - num_outliers - num_dirty  # 100,000

    print(f" -> Segmento limpio base: {num_clean:,} (80.0%)")
    print(f" -> Segmento outliers:    {num_outliers:,} (10.0%)")
    print(f" -> Segmento sucio/nulo:  {num_dirty:,} (10.0%)")

    # 1. GENERACION BASE NOMINAL (125,000 filas base coherentes)
    record_ids = [f"REC-{i:06d}" for i in range(1, total_records + 1)]

    # Fechas entre 2026-01-01 y 2026-10-31
    start_dt = datetime(2026, 1, 1, 0, 0, 0)
    end_dt = datetime(2026, 10, 31, 23, 59, 59)
    total_seconds = int((end_dt - start_dt).total_seconds())
    random_seconds = np.random.randint(0, total_seconds, size=total_records)
    timestamps = [start_dt + timedelta(seconds=int(s)) for s in random_seconds]

    selected_drones = np.random.choice(drone_ids, size=total_records)
    selected_classes = np.random.choice(drone_classes, size=total_records, p=drone_class_weights)
    selected_patterns = np.random.choice(flight_patterns, size=total_records, p=pattern_weights)
    selected_weathers = np.random.choice(weather_conditions, size=total_records, p=weather_weights)

    # 60% Bucaramanga, 40% Bogota
    city_choices = np.random.choice(["Bucaramanga", "Bogota"], size=total_records, p=[0.60, 0.40])
    selected_sensors = []
    latitudes = np.empty(total_records, dtype=float)
    longitudes = np.empty(total_records, dtype=float)

    for i in range(total_records):
        city = city_choices[i]
        if city == "Bucaramanga":
            selected_sensors.append(np.random.choice(sensors_bga))
            latitudes[i] = 7.119 + np.random.normal(0, 0.025)
            longitudes[i] = -73.122 + np.random.normal(0, 0.025)
        else:
            selected_sensors.append(np.random.choice(sensors_bog))
            latitudes[i] = 4.609 + np.random.normal(0, 0.035)
            longitudes[i] = -74.081 + np.random.normal(0, 0.035)

    # Variables cinematicas y operativas normales
    altitudes = np.random.uniform(10.0, 280.0, size=total_records)
    speeds = np.random.uniform(0.5, 32.0, size=total_records)
    vertical_speeds = np.random.uniform(-8.0, 12.0, size=total_records)
    headings = np.random.uniform(0.0, 359.9, size=total_records)
    distances = np.random.uniform(20.0, 1950.0, size=total_records)
    rf_signals = np.random.uniform(-105.0, -35.0, size=total_records)
    batteries = np.random.uniform(8.0, 99.0, size=total_records)
    confidences = np.random.uniform(0.45, 0.98, size=total_records)
    wind_speeds = np.random.uniform(3.0, 42.0, size=total_records)

    # Calculo logico deterministico de Threat Level (Target)
    threat_levels = []
    for i in range(total_records):
        d_class = selected_classes[i]
        if d_class == "bird_false_pos":
            threat_levels.append("LOW")
            continue

        score = 0.0

        # Clase de dron
        if d_class == "diy_custom":
            score += 26.0
        elif d_class == "fixed_wing":
            score += 22.0
        elif d_class == "hexacopter":
            score += 16.0
        else:  # quadcopter
            score += 10.0

        # Proximidad a la zona critica protegida
        dist = distances[i]
        if dist < 120.0:
            score += 48.0
        elif dist < 350.0:
            score += 32.0
        elif dist < 750.0:
            score += 18.0
        elif dist > 1400.0:
            score -= 15.0

        # Velocidad horizontal
        spd = speeds[i]
        if spd > 22.0:
            score += 24.0
        elif spd > 12.0:
            score += 14.0

        # Altitud
        alt = altitudes[i]
        if alt > 120.0:  # Violacion de cota reglamentaria 120m
            score += 18.0

        # Patron de vuelo
        pat = selected_patterns[i]
        if pat == "Evasivo":
            score += 28.0
        elif pat == "Directo":
            score += 22.0
        elif pat == "Patrullaje":
            score += 12.0
        elif pat == "Erratico":
            score += 8.0

        # Potencia RF (cercania de la antena de control)
        if rf_signals[i] > -50.0:
            score += 10.0

        # Confianza IA
        if confidences[i] > 0.85:
            score += 8.0

        # Ruido natural leve para simular incertidumbre operacional minima
        score += np.random.normal(0, 1.2)

        # Mapeo a las 4 categorias estandar con limites claros
        if score < 35.0:
            threat_levels.append("LOW")
        elif score < 65.0:
            threat_levels.append("MEDIUM")
        elif score < 100.0:
            threat_levels.append("HIGH")
        else:
            threat_levels.append("CRITICAL")

    # Armado del DataFrame inicial
    df = pd.DataFrame({
        "record_id": record_ids,
        "timestamp": timestamps,
        "drone_id": selected_drones,
        "sensor_id": selected_sensors,
        "city_zone": city_choices,
        "latitude": np.round(latitudes, 6),
        "longitude": np.round(longitudes, 6),
        "altitude_m": np.round(altitudes, 2),
        "speed_ms": np.round(speeds, 2),
        "vertical_speed_ms": np.round(vertical_speeds, 2),
        "heading_deg": np.round(headings, 2),
        "distance_to_zone_m": np.round(distances, 2),
        "rf_signal_dbm": np.round(rf_signals, 2),
        "battery_est_pct": np.round(batteries, 2),
        "ai_confidence": np.round(confidences, 4),
        "drone_class": selected_classes,
        "weather_condition": selected_weathers,
        "wind_speed_kmh": np.round(wind_speeds, 2),
        "flight_pattern": selected_patterns,
        "threat_level": threat_levels
    })

    # 2. INYECCION DE OUTLIERS EXTREMOS (Exactamente 10% = 12,500 registros)
    print("\n -> Inyectando 10% (12,500) outliers extremos...")
    outlier_indices = np.random.choice(range(num_clean, num_clean + num_outliers), size=num_outliers, replace=False)

    # Cuartiles de outliers
    split_size = num_outliers // 4
    idx_alt = outlier_indices[:split_size]
    idx_spd = outlier_indices[split_size:split_size * 2]
    idx_dist = outlier_indices[split_size * 2:split_size * 3]
    idx_wind = outlier_indices[split_size * 3:]

    # Altitudes estratosfericas (3500m - 9000m) o negativas aberrantes (-200m)
    alt_noise = np.random.choice([1, -1], size=len(idx_alt), p=[0.85, 0.15])
    df.loc[idx_alt, "altitude_m"] = np.where(
        alt_noise == 1,
        np.round(np.random.uniform(3500.0, 9000.0, size=len(idx_alt)), 2),
        np.round(np.random.uniform(-200.0, -15.0, size=len(idx_alt)), 2)
    )

    # Velocidades supersonicas aberrantes para drones comerciales (300 a 650 m/s)
    df.loc[idx_spd, "speed_ms"] = np.round(np.random.uniform(300.0, 650.0, size=len(idx_spd)), 2)

    # Distancias radar colosales (> 150 km)
    df.loc[idx_dist, "distance_to_zone_m"] = np.round(np.random.uniform(150000.0, 350000.0, size=len(idx_dist)), 2)

    # Viento huracanado categoria 5 (> 250 km/h)
    df.loc[idx_wind, "wind_speed_kmh"] = np.round(np.random.uniform(255.0, 380.0, size=len(idx_wind)), 2)

    # 3. INYECCION DE SUCIEDAD, ERRORES, NULOS Y DUPLICADOS (10% = 12,500 registros)
    dirty_start = num_clean + num_outliers
    dirty_indices = list(range(dirty_start, total_records))
    np.random.shuffle(dirty_indices)

    # 3.5% Nulos (4,375 registros)
    num_nulls = int(total_records * 0.035)
    null_idx = dirty_indices[:num_nulls]
    print(f" -> Inyectando 3.5% ({num_nulls:,}) nulos (NaN/None)...")

    # Inyectar NaN en columnas clave
    cols_to_null = ["rf_signal_dbm", "ai_confidence", "weather_condition", "altitude_m", "battery_est_pct"]
    for idx in null_idx:
        target_col = np.random.choice(cols_to_null)
        df.loc[idx, target_col] = np.nan

    # 3.5% Valores Corruptos / Imposibles (4,375 registros)
    num_corrupt = int(total_records * 0.035)
    corrupt_idx = dirty_indices[num_nulls:num_nulls + num_corrupt]
    print(f" -> Inyectando 3.5% ({num_corrupt:,}) datos corruptos / rangos imposibles...")

    c_split = num_corrupt // 4
    # ai_confidence fuera de rango [0, 1] (ej. 2.45 o -0.80)
    df.loc[corrupt_idx[:c_split], "ai_confidence"] = np.random.choice([2.45, 3.80, -0.80, -1.50], size=c_split)

    # battery_est_pct fuera de rango [0, 100] (ej. 320% o -45%)
    df.loc[corrupt_idx[c_split:c_split * 2], "battery_est_pct"] = np.random.choice([320.0, 450.0, -45.0, -10.0], size=c_split)

    # heading_deg fuera de [0, 360] (ej. 890 o 1200)
    df.loc[corrupt_idx[c_split * 2:c_split * 3], "heading_deg"] = np.random.choice([720.0, 890.0, 1250.0, -180.0], size=c_split)

    # Strings corruptos en categorias o numericos ("SENSOR_ERR", "???")
    df["rf_signal_dbm"] = df["rf_signal_dbm"].astype(object)
    df["altitude_m"] = df["altitude_m"].astype(object)
    df["speed_ms"] = df["speed_ms"].astype(object)

    for idx in corrupt_idx[c_split * 3:]:
        c_choice = np.random.choice(["weather_condition", "drone_class", "flight_pattern", "rf_signal_dbm", "altitude_m", "speed_ms"])
        df.loc[idx, c_choice] = np.random.choice(["SENSOR_ERR", "???", "CORRUPTED_HEX_0xFF"])

    # 3.0% Duplicados exactos (3,750 registros)
    num_dupes = total_records - (num_clean + num_outliers + num_nulls + num_corrupt)  # 3,750
    dupe_dest_idx = dirty_indices[num_nulls + num_corrupt:]
    source_dupe_idx = np.random.choice(range(0, num_clean), size=len(dupe_dest_idx), replace=False)
    print(f" -> Inyectando 3.0% ({len(dupe_dest_idx):,}) filas duplicadas exactas...")

    # Inyectamos duplicados exactos operando columna por columna (ultra rapido en pandas 3.0)
    for col in df.columns:
        df.loc[dupe_dest_idx, col] = df.loc[source_dupe_idx, col].values

    # Guardar CSV
    print(f"\n Guardando dataset en: {csv_path} ...")
    df.to_csv(csv_path, index=False)
    file_size_mb = os.path.getsize(csv_path) / (1024 * 1024)

    print("=" * 70)
    print(f" [SUCCESS] Dataset generado exitosamente!")
    print(f"  - Filas totales:    {len(df):,}")
    print(f"  - Columnas:         {len(df.columns)}")
    print(f"  - Tamano en disco:  {file_size_mb:.2f} MB")
    print(f"  - Distribucion Threat Level:")
    print(df['threat_level'].value_counts())
    print("=" * 70)

if __name__ == "__main__":
    generate_aeroguard_dataset()
