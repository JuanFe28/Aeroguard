#!/usr/bin/env python3
"""
AeroGuard C-UAS — Pipeline Automatizado de Mineria de Datos (CRISP-DM Fases 2 a 6)
Ejecuta:
- Fase 2: Comprension de Datos (EDA, Deteccion de Outliers IQR y Graficos Iniciales)
- Fase 3: Preparacion de Datos (Limpieza, Imputacion, Encoding, Escalado, Dataset Limpio >= 105k)
- Fase 4 y 5: Modelado y Evaluacion Comparativa (Random Forest vs Decision Tree)
- Fase 6: Despliegue y Reglas de Conocimiento (Exportacion .pkl e Insights Operacionales)
"""

import json
import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limpieza import clean_telemetry  # noqa: E402

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)

# Configuracion visual
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8


def compute_knowledge_rules(df):
    """Calcula las reglas de conocimiento sobre el dataset limpio y devuelve porcentajes reales."""
    hc = df["threat_level"].isin(["HIGH", "CRITICAL"])
    crit = df["threat_level"] == "CRITICAL"

    c1 = (df["distance_to_zone_m"] < 150) & (df["speed_ms"] > 20) & df["flight_pattern"].isin(["Directo", "Evasivo"])
    c2 = (df["altitude_m"] > 120) & df["drone_class"].isin(["diy_custom", "fixed_wing"])
    birds = df["drone_class"] == "bird_false_pos"
    c4 = df["rf_signal_dbm"] > -50

    def pct(mask):
        return round(float(mask.mean()) * 100, 1) if len(mask) else 0.0

    return {
        "nota": "Calculado sobre el dataset sintetico limpio; threat_level proviene del puntaje del generador.",
        "registros_limpios": int(len(df)),
        "r1": {"n": int(c1.sum()), "pct_critical": pct(crit[c1]), "pct_critical_base": pct(crit)},
        "r2": {"n": int(c2.sum()), "pct_hc_cond": pct(hc[c2]), "pct_hc_resto": pct(hc[~c2]),
               "diff_pp": round(pct(hc[c2]) - pct(hc[~c2]), 1)},
        "r3": {"n": int(birds.sum()), "pct_low": pct(df.loc[birds, "threat_level"] == "LOW")},
        "r4": {"n": int(c4.sum()), "pct_hc_cond": pct(hc[c4]), "pct_hc_resto": pct(hc[~c4])},
    }


def run_crisp_dm_pipeline():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    models_dir = os.path.join(base_dir, "models")
    reports_dir = os.path.join(base_dir, "reports")
    figures_dir = os.path.join(reports_dir, "figures")

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    raw_csv = os.path.join(data_dir, "aeroguard_raw_telemetry.csv")
    clean_csv = os.path.join(data_dir, "aeroguard_clean_telemetry.csv")
    model_path = os.path.join(models_dir, "aeroguard_threat_model.pkl")

    if not os.path.exists(raw_csv):
        print(f"[ERROR] No se encontro el archivo {raw_csv}. Ejecute primero 01_generate_dataset.py")
        sys.exit(1)

    print("\n" + "=" * 75)
    print(" [AEROGUARD C-UAS] PIPELINE COMPLETO DE MINERIA DE DATOS (CRISP-DM)")
    print("=" * 75)

    # =========================================================================
    # FASE 2: COMPRENSION DE LOS DATOS (EDA ANTES DE LIMPIAR)
    # =========================================================================
    print("\n>>> [CRISP-DM FASE 2] Comprension e Identificacion de los Datos...")
    df_raw = pd.read_csv(raw_csv, low_memory=False)
    total_raw = len(df_raw)
    print(f" -> Registros brutos cargados: {total_raw:,} | Columnas: {len(df_raw.columns)}")

    # 1. Conteo de Duplicados
    raw_duplicates = df_raw.duplicated().sum()
    pct_dupes = (raw_duplicates / total_raw) * 100
    print(f" -> Filas duplicadas exactas: {raw_duplicates:,} ({pct_dupes:.2f}%)")

    # 2. Conteo de Nulos y valores corruptos
    print("\n --- Analisis de Calidad y Tipos de Datos Sucios ---")
    corrupt_tokens = ["SENSOR_ERR", "???", "CORRUPTED_HEX_0xFF"]

    # Identificar celdas con errores de conversion en columnas supuestamente numericas
    numeric_candidate_cols = [
        "latitude", "longitude", "altitude_m", "speed_ms", "vertical_speed_ms",
        "heading_deg", "distance_to_zone_m", "rf_signal_dbm", "battery_est_pct",
        "ai_confidence", "wind_speed_kmh"
    ]

    dirty_summary = {}
    for col in df_raw.columns:
        n_nulls = df_raw[col].isna().sum()
        # Conteo de strings corruptos
        n_corrupt = df_raw[col].astype(str).isin(corrupt_tokens).sum()
        dirty_summary[col] = {
            "nulos": n_nulls,
            "corruptos": n_corrupt,
            "total_sucios": n_nulls + n_corrupt,
            "pct_sucio": ((n_nulls + n_corrupt) / total_raw) * 100
        }

    # 3. Deteccion de Outliers por IQR en variables cinematicas clave
    # Coercionar a numerico para poder calcular IQR en crudo
    alt_raw_num = pd.to_numeric(df_raw["altitude_m"], errors="coerce")
    spd_raw_num = pd.to_numeric(df_raw["speed_ms"], errors="coerce")
    dst_raw_num = pd.to_numeric(df_raw["distance_to_zone_m"], errors="coerce")

    def calc_iqr_outliers(series):
        valid = series.dropna()
        q1 = valid.quantile(0.25)
        q3 = valid.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = valid[(valid < lower) | (valid > upper)]
        return len(outliers), lower, upper

    n_out_alt, alt_low, alt_up = calc_iqr_outliers(alt_raw_num)
    n_out_spd, spd_low, spd_up = calc_iqr_outliers(spd_raw_num)
    n_out_dst, dst_low, dst_up = calc_iqr_outliers(dst_raw_num)

    print(f" -> Outliers IQR altitude_m:        {n_out_alt:,} fuera de [{alt_low:.1f}, {alt_up:.1f}]")
    print(f" -> Outliers IQR speed_ms:           {n_out_spd:,} fuera de [{spd_low:.1f}, {spd_up:.1f}]")
    print(f" -> Outliers IQR distance_to_zone_m: {n_out_dst:,} fuera de [{dst_low:.1f}, {dst_up:.1f}]")

    # FIGURA 01: Boxplot de Outliers Antes de Limpiar
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("Fase 2: Detección de Outliers Extremos en Telemetría Bruta (AeroGuard C-UAS)", fontsize=14, fontweight="bold", y=1.02)

    sns.boxplot(y=alt_raw_num, ax=axes[0], color="#e74c3c")
    axes[0].set_title(f"Altitud (m)\n(Outliers: {n_out_alt:,} reg)", fontsize=11, fontweight="bold")
    axes[0].set_ylabel("Metros (Escala extendida con anomalías > 3,500m)")

    sns.boxplot(y=spd_raw_num, ax=axes[1], color="#e67e22")
    axes[1].set_title(f"Velocidad Horizontal (m/s)\n(Outliers supersónicos > 300 m/s)", fontsize=11, fontweight="bold")
    axes[1].set_ylabel("m/s")

    sns.boxplot(y=dst_raw_num / 1000.0, ax=axes[2], color="#9b59b6")
    axes[2].set_title(f"Distancia a Zona Protegida (km)\n(Outliers radar > 150 km)", fontsize=11, fontweight="bold")
    axes[2].set_ylabel("Kilómetros")

    plt.tight_layout()
    fig1_path = os.path.join(figures_dir, "01_boxplot_outliers_antes.png")
    plt.savefig(fig1_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f" -> [GRAFICO] Guardado: {fig1_path}")

    # FIGURA 02: Mapa / Barras de Calidad de Datos (Nulos, Corruptos, Duplicados)
    fig, ax = plt.subplots(figsize=(12, 6))
    df_quality = pd.DataFrame(dirty_summary).T.sort_values(by="pct_sucio", ascending=False)
    top_dirty = df_quality[df_quality["total_sucios"] > 0]

    # Agregamos los duplicados a la visualizacion
    labels = list(top_dirty.index) + ["FILAS DUPLICADAS"]
    pcts = list(top_dirty["pct_sucio"]) + [pct_dupes]
    colors = ["#e74c3c" if p > 3.0 else "#3498db" for p in pcts]

    bars = ax.barh(labels, pcts, color=colors, edgecolor="#333333", alpha=0.85)
    ax.set_xlabel("Porcentaje del Total de Datos (%)", fontweight="bold")
    ax.set_title("Fase 2: Mapa de Calidad de Datos — Porcentaje de Ruido, Nulos y Duplicados", fontsize=13, fontweight="bold")
    ax.axvline(3.5, color="#e67e22", linestyle="--", linewidth=1.2, label="Umbral de Inyección de Ruido (3.5%)")

    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.1, bar.get_y() + bar.get_height() / 2, f"{w:.2f}%", va="center", fontsize=9, fontweight="bold")

    ax.legend(loc="lower right")
    plt.tight_layout()
    fig2_path = os.path.join(figures_dir, "02_mapa_nulos_y_calidad.png")
    plt.savefig(fig2_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f" -> [GRAFICO] Guardado: {fig2_path}")

    # =========================================================================
    # FASE 3: PREPARACION Y PREPROCESAMIENTO DE LOS DATOS
    # =========================================================================
    print("\n>>> [CRISP-DM FASE 3] Preparacion y Preprocesamiento de los Datos...")

    # Limpieza compartida con 03_export_orange.py (ver limpieza.py)
    df_clean, clean_summary = clean_telemetry(df_raw)
    print(f" -> Filas tras deduplicacion: {total_raw - clean_summary['duplicados_eliminados']:,} "
          f"(eliminadas: {clean_summary['duplicados_eliminados']:,})")
    print(f" -> Filas tras filtrado de anomalias fisicas extremas: {len(df_clean):,}")

    # Verificacion estricta del requisito: Dataset limpio >= 105,000 registros
    if len(df_clean) < 105000:
        print(f"[ADVERTENCIA] El dataset tiene {len(df_clean)} filas (< 105,000).")
    else:
        print(f" -> [OK] Cumple requisito de tamano limpio: {len(df_clean):,} >= 105,000 registros")

    # Guardar dataset limpio en CSV
    df_clean.to_csv(clean_csv, index=False)
    clean_size_mb = os.path.getsize(clean_csv) / (1024 * 1024)
    print(f" -> Dataset limpio guardado en: {clean_csv} ({clean_size_mb:.2f} MB)")

    # FIGURA 03: Boxplot Limpio Despues de Tratar Outliers
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("Fase 3: Distribución Normalizada de Telemetría tras Limpieza y Filtrado (AeroGuard C-UAS)", fontsize=14, fontweight="bold", y=1.02)

    sns.boxplot(y=df_clean["altitude_m"], ax=axes[0], color="#2ecc71")
    axes[0].set_title("Altitud Limpia (m)\n(Techo operativo nominal)", fontsize=11, fontweight="bold")
    axes[0].set_ylabel("Metros")

    sns.boxplot(y=df_clean["speed_ms"], ax=axes[1], color="#3498db")
    axes[1].set_title("Velocidad Horizontal Limpia (m/s)\n(Rango realista C-UAS)", fontsize=11, fontweight="bold")
    axes[1].set_ylabel("m/s")

    sns.boxplot(y=df_clean["distance_to_zone_m"], ax=axes[2], color="#1abc9c")
    axes[2].set_title("Distancia a Zona Protegida (m)\n(Alcance perimetral)", fontsize=11, fontweight="bold")
    axes[2].set_ylabel("Metros")

    plt.tight_layout()
    fig3_path = os.path.join(figures_dir, "03_boxplot_limpio_despues.png")
    plt.savefig(fig3_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f" -> [GRAFICO] Guardado: {fig3_path}")

    # Mapeo ordinal para Threat Level
    threat_map = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    df_clean["threat_level_num"] = df_clean["threat_level"].map(threat_map)

    # FIGURA 04: Matriz de Correlacion Cinematica y Táctica
    corr_cols = numeric_candidate_cols + ["threat_level_num"]
    corr_matrix = df_clean[corr_cols].corr()

    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(
        corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", cbar=True,
        linewidths=0.5, ax=ax, vmin=-1, vmax=1
    )
    ax.set_title("Fase 3: Matriz de Correlación de Pearson (Variables Físicas vs Nivel de Amenaza)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig4_path = os.path.join(figures_dir, "04_matriz_correlacion.png")
    plt.savefig(fig4_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f" -> [GRAFICO] Guardado: {fig4_path}")

    # =========================================================================
    # FASE 4 Y 5: MODELADO, ENTRENAMIENTO Y EVALUACION COMPARATIVA
    # =========================================================================
    print("\n>>> [CRISP-DM FASE 4 Y 5] Modelado y Evaluacion Comparativa...")

    # Seleccion y Codificacion de Features
    features_numeric = [
        "altitude_m", "speed_ms", "vertical_speed_ms", "heading_deg",
        "distance_to_zone_m", "rf_signal_dbm", "battery_est_pct",
        "ai_confidence", "wind_speed_kmh"
    ]
    features_categorical = ["drone_class", "flight_pattern", "weather_condition", "city_zone"]

    # Codificadores de categorias
    encoders = {}
    df_features = df_clean[features_numeric].copy()
    for cat_col in features_categorical:
        le = LabelEncoder()
        df_features[cat_col] = le.fit_transform(df_clean[cat_col].astype(str))
        encoders[cat_col] = le

    feature_names = list(df_features.columns)
    X = df_features.values
    y = df_clean["threat_level"].values

    # Escalado estandar
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Division 80% Entrenamiento / 20% Prueba estratificada
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f" -> Conjunto de Entrenamiento: {X_train.shape[0]:,} registros")
    print(f" -> Conjunto de Prueba:        {X_test.shape[0]:,} registros")
    print(f" -> Numero de Variables (Features): {len(feature_names)}")

    # Modelo 1: Random Forest Classifier
    print("\n --- Entrenando Modelo 1: Random Forest Classifier ---")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=16,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    y_pred_rf = rf_model.predict(X_test)

    acc_rf = accuracy_score(y_test, y_pred_rf)
    prec_rf = precision_score(y_test, y_pred_rf, average="weighted")
    rec_rf = recall_score(y_test, y_pred_rf, average="weighted")
    f1_rf = f1_score(y_test, y_pred_rf, average="weighted")
    f1_macro_rf = f1_score(y_test, y_pred_rf, average="macro")

    print(f"  [Random Forest] Accuracy: {acc_rf:.4f} ({acc_rf*100:.2f}%)")
    print(f"  [Random Forest] Precision (Weighted): {prec_rf:.4f}")
    print(f"  [Random Forest] Recall (Weighted):    {rec_rf:.4f}")
    print(f"  [Random Forest] F1-Score (Weighted):  {f1_rf:.4f}")
    print(f"  [Random Forest] F1-Score (Macro):     {f1_macro_rf:.4f}")

    # Modelo 2: Decision Tree Classifier
    print("\n --- Entrenando Modelo 2: Decision Tree Classifier ---")
    dt_model = DecisionTreeClassifier(
        max_depth=12,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42
    )
    dt_model.fit(X_train, y_train)
    y_pred_dt = dt_model.predict(X_test)

    acc_dt = accuracy_score(y_test, y_pred_dt)
    prec_dt = precision_score(y_test, y_pred_dt, average="weighted")
    rec_dt = recall_score(y_test, y_pred_dt, average="weighted")
    f1_dt = f1_score(y_test, y_pred_dt, average="weighted")
    f1_macro_dt = f1_score(y_test, y_pred_dt, average="macro")

    print(f"  [Decision Tree] Accuracy: {acc_dt:.4f} ({acc_dt*100:.2f}%)")
    print(f"  [Decision Tree] Precision (Weighted): {prec_dt:.4f}")
    print(f"  [Decision Tree] Recall (Weighted):    {rec_dt:.4f}")
    print(f"  [Decision Tree] F1-Score (Weighted):  {f1_dt:.4f}")
    print(f"  [Decision Tree] F1-Score (Macro):     {f1_macro_dt:.4f}")

    # Tabla Comparativa de Modelos
    print("\n" + "=" * 70)
    print(" TABLA COMPARATIVA DE MODELOS SUPERVISADOS (CRISP-DM FASE 5)")
    print("=" * 70)
    df_eval = pd.DataFrame({
        "Modelo": ["Random Forest Classifier", "Decision Tree Classifier"],
        "Accuracy": [f"{acc_rf*100:.2f}%", f"{acc_dt*100:.2f}%"],
        "Precision (W)": [f"{prec_rf:.4f}", f"{prec_dt:.4f}"],
        "Recall (W)": [f"{rec_rf:.4f}", f"{rec_dt:.4f}"],
        "F1-Score (W)": [f"{f1_rf:.4f}", f"{f1_dt:.4f}"],
        "F1-Score (Macro)": [f"{f1_macro_rf:.4f}", f"{f1_macro_dt:.4f}"]
    })
    print(df_eval.to_string(index=False))

    # Seleccion del mejor modelo
    best_model = rf_model if f1_rf >= f1_dt else dt_model
    best_name = "Random Forest" if best_model == rf_model else "Decision Tree"
    best_preds = y_pred_rf if best_model == rf_model else y_pred_dt
    print(f"\n -> [SELECCION] El mejor modelo es: {best_name} (F1: {max(f1_rf, f1_dt):.4f})")

    # Classification Report
    target_labels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    print("\n --- Classification Report Detallado ---")
    print(classification_report(y_test, best_preds, labels=target_labels))

    # FIGURA 05: Matriz de Confusion
    cm = confusion_matrix(y_test, best_preds, labels=target_labels)
    cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    fig, ax = plt.subplots(figsize=(8, 6.5))
    sns.heatmap(
        cm_norm, annot=True, fmt=".2%", cmap="Blues", cbar=True,
        xticklabels=target_labels, yticklabels=target_labels, ax=ax,
        annot_kws={"size": 11, "fontweight": "bold"}
    )
    ax.set_title(f"Fase 5: Matriz de Confusión Normalizada — {best_name}\n(Accuracy Global: {max(acc_rf, acc_dt)*100:.2f}%)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Predicción del Modelo", fontweight="bold")
    ax.set_ylabel("Valor Real de Telemetría", fontweight="bold")
    plt.tight_layout()
    fig5_path = os.path.join(figures_dir, "05_matriz_confusion.png")
    plt.savefig(fig5_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f" -> [GRAFICO] Guardado: {fig5_path}")

    # FIGURA 06: Importancia de Variables (Feature Importance)
    importances = best_model.feature_importances_
    feat_df = pd.DataFrame({
        "Feature": feature_names,
        "Importancia": importances
    }).sort_values(by="Importancia", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6.5))
    bars = ax.barh(feat_df["Feature"], feat_df["Importancia"], color="#2980b9", edgecolor="#1a5276", alpha=0.9)
    ax.set_xlabel("Ganancia de Información (Gini Importance)", fontweight="bold")
    ax.set_title(f"Fase 5: Ranking de Importancia de Variables en la Detección de Amenaza\n(Modelo: {best_name})", fontsize=13, fontweight="bold")

    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.005, bar.get_y() + bar.get_height() / 2, f"{w*100:.1f}%", va="center", fontsize=9, fontweight="bold")

    plt.tight_layout()
    fig6_path = os.path.join(figures_dir, "06_importancia_variables_feature_importance.png")
    plt.savefig(fig6_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f" -> [GRAFICO] Guardado: {fig6_path}")

    # =========================================================================
    # FASE 6: CONOCIMIENTO Y DESPLIEGUE OPERACIONAL
    # =========================================================================
    print("\n>>> [CRISP-DM FASE 6] Generacion de Conocimiento y Despliegue...")

    # Empaquetado del modelo para despliegue
    model_bundle = {
        "model": best_model,
        "model_name": best_name,
        "feature_names": feature_names,
        "scaler": scaler,
        "encoders": encoders,
        "metrics": {
            "accuracy": float(max(acc_rf, acc_dt)),
            "f1_weighted": float(max(f1_rf, f1_dt)),
            "f1_macro": float(max(f1_macro_rf, f1_macro_dt))
        },
        "version": "1.0.0-crisp-dm",
        "target_mapping": target_labels
    }

    joblib.dump(model_bundle, model_path)
    model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
    print(f" -> Modelo y transformadores serializados en: {model_path} ({model_size_mb:.2f} MB)")

    # Reglas de conocimiento: se CALCULAN sobre el dataset limpio (no son valores fijos).
    # Nota: threat_level lo asigna el generador sintetico con un puntaje por reglas,
    # por eso estas reglas describen el generador, no comportamiento real de drones.
    rules = compute_knowledge_rules(df_clean)
    rules_path = os.path.join(reports_dir, "reglas_conocimiento.json")
    with open(rules_path, "w", encoding="utf-8") as fh:
        json.dump(rules, fh, ensure_ascii=False, indent=2)

    r1, r2, r3, r4 = rules["r1"], rules["r2"], rules["r3"], rules["r4"]
    print("\n" + "=" * 75)
    print(" REGLAS DE CONOCIMIENTO CALCULADAS SOBRE EL DATASET LIMPIO (SINTETICO)")
    print("=" * 75)
    print(" 1. PROXIMIDAD PERIMETRAL Y VELOCIDAD:")
    print("    - Si 'distance_to_zone_m' < 150m y 'speed_ms' > 20 m/s con patron 'Directo' o 'Evasivo',")
    print(f"      el {r1['pct_critical']:.1f}% de los {r1['n']:,} eventos son CRITICAL "
          f"(base general: {r1['pct_critical_base']:.1f}%).")
    print("\n 2. TECHO DE 120 m AGL Y DRONES NO COMERCIALES:")
    print("    - Con altitud > 120 m y tipo 'diy_custom' o 'fixed_wing', HIGH/CRITICAL es "
          f"{r2['pct_hc_cond']:.1f}% frente a {r2['pct_hc_resto']:.1f}% en el resto "
          f"({r2['diff_pp']:+.1f} puntos porcentuales, n={r2['n']:,}).")
    print("\n 3. AVES (FALSOS POSITIVOS):")
    print(f"    - De {r3['n']:,} registros 'bird_false_pos', el {r3['pct_low']:.1f}% es LOW.")
    print("\n 4. SENAL RF:")
    print(f"    - Con RF > -50 dBm, HIGH/CRITICAL es {r4['pct_hc_cond']:.1f}% frente a "
          f"{r4['pct_hc_resto']:.1f}% con RF <= -50 dBm (n={r4['n']:,}).")
    print(f"\n -> Reglas guardadas en: {rules_path}")
    print("=" * 75)
    print(" [SUCCESS] Pipeline CRISP-DM completado exitosamente con todas las fases!")

if __name__ == "__main__":
    run_crisp_dm_pipeline()
