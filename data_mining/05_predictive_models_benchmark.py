#!/usr/bin/env python3
"""
AeroGuard C-UAS — Benchmark Predictivo Integral de 6 Modelos (CRISP-DM + Artefacto Runtime)

Evalua sin fuga de datos (split previo a cualquier fit) los 6 algoritmos obligatorios:
1. Regresion Lineal      -> Puntaje continuo de riesgo cinematico (risk_score, 0-100)
2. Regresion Logistica   -> Probabilidad de alto riesgo / violacion de geocerca + umbral optimo
3. K-Means               -> Descubrimiento no supervisado de perfiles de vuelo (codo + Silhouette)
4. Arbol de Decision     -> Reglas interpretables para threat_level (4 clases)
5. Random Forest         -> Ensamble robusto para clasificacion threat_level en produccion
6. ARIMA                 -> Pronostico temporal diario de picos de incursiones HIGH/CRITICAL

Genera:
- 4 graficas de evidencia en data_mining/reports/figures/ (300 DPI)
- data_mining/reports/comparativa_6_modelos.json
- backend/app/data/predictive_models_artifact.json (inferencia liviana pure-numpy sin sklearn en Docker)
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    precision_score,
    recall_score,
    r2_score,
    roc_auc_score,
    roc_curve,
    root_mean_squared_error,
    silhouette_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from statsmodels.tsa.arima.model import ARIMA

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))
from limpieza import clean_telemetry, compute_risk_score  # noqa: E402

NUMERIC_FEATURES = [
    "altitude_m",
    "speed_ms",
    "vertical_speed_ms",
    "heading_deg",
    "distance_to_zone_m",
    "rf_signal_dbm",
    "battery_est_pct",
    "ai_confidence",
    "wind_speed_kmh",
]
CATEGORICAL_FEATURES = ["drone_class", "flight_pattern", "weather_condition", "city_zone"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
KMEANS_FEATURES = [
    "distance_to_zone_m",
    "altitude_m",
    "speed_ms",
]
TARGET_LABELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams["font.sans-serif"] = "DejaVu Sans"


def _make_tree_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "cat",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


def _make_linear_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        remainder="drop",
    )


def _export_tree(estimator: DecisionTreeClassifier) -> dict[str, Any]:
    tree = estimator.tree_
    children_left = tree.children_left.tolist()
    children_right = tree.children_right.tolist()
    feature = tree.feature.tolist()
    threshold = [float(t) for t in tree.threshold.tolist()]
    leaf_probs: dict[str, list[float]] = {}
    for idx in range(tree.node_count):
        if children_left[idx] == -1:
            counts = tree.value[idx][0]
            total = float(counts.sum()) or 1.0
            leaf_probs[str(idx)] = [round(float(c / total), 5) for c in counts]
    return {
        "children_left": children_left,
        "children_right": children_right,
        "feature": feature,
        "threshold": threshold,
        "leaf_probs": leaf_probs,
    }


def _predict_exported_rf(X_row: np.ndarray, trees: list[dict[str, Any]], classes: list[str]) -> tuple[str, np.ndarray]:
    n_classes = len(classes)
    avg_probs = np.zeros(n_classes, dtype=float)
    for t in trees:
        node = 0
        cl = t["children_left"]
        cr = t["children_right"]
        feat = t["feature"]
        thr = t["threshold"]
        while cl[node] != -1:
            f_idx = feat[node]
            node = cl[node] if X_row[f_idx] <= thr[node] else cr[node]
        avg_probs += np.asarray(t["leaf_probs"][str(node)], dtype=float)
    avg_probs /= float(len(trees))
    return classes[int(np.argmax(avg_probs))], avg_probs


def _label_kmeans_clusters(centroids_phys: pd.DataFrame, high_risk_rates: list[float]) -> list[dict[str, Any]]:
    """Asigna etiquetas tacticas interpretables y unicas a los k centroides."""
    labels_assigned: dict[int, tuple[str, str]] = {}
    remaining = set(range(len(centroids_phys)))

    # 1. Perfil de menor distancia al perimetro protegido
    idx_closest = min(remaining, key=lambda i: centroids_phys.iloc[i]["distance_to_zone_m"])
    labels_assigned[idx_closest] = (
        "Aproximación Cercana al Perímetro",
        "Contactos con menor distancia radial hacia la zona protegida.",
    )
    remaining.remove(idx_closest)

    # 2. Entre los restantes, mayor altitud promedio (sobre cota 120 m)
    idx_high_alt = max(remaining, key=lambda i: centroids_phys.iloc[i]["altitude_m"])
    labels_assigned[idx_high_alt] = (
        "Sobrevuelo Elevado (Sobre Cota 120 m)",
        "Aeronaves operando por encima del techo civil de referencia.",
    )
    remaining.remove(idx_high_alt)

    # 3. Entre los restantes, mayor velocidad horizontal promedio
    idx_fast = max(remaining, key=lambda i: centroids_phys.iloc[i]["speed_ms"])
    labels_assigned[idx_fast] = (
        "Tránsito Rápido Perimetral",
        "Desplazamiento horizontal veloz en zonas medias o aproximación.",
    )
    remaining.remove(idx_fast)

    # 4. Restante: vuelo distante / menor presion cinematica
    for idx_rem in remaining:
        labels_assigned[idx_rem] = (
            "Vuelo Distante / Baja Energía",
            "Contactos alejados del núcleo protegido y velocidad moderada/baja.",
        )

    profiles: list[dict[str, Any]] = []
    for cid in range(len(centroids_phys)):
        lbl, desc = labels_assigned[cid]
        row = centroids_phys.iloc[cid]
        profiles.append(
            {
                "cluster_id": int(cid),
                "label": lbl,
                "description": desc,
                "high_risk_rate_pct": round(float(high_risk_rates[cid]), 2),
                "centroid_physical": {col: round(float(row[col]), 3) for col in KMEANS_FEATURES},
            }
        )
    return profiles


def run_benchmark() -> dict[str, Any]:
    data_dir = BASE_DIR / "data"
    reports_dir = BASE_DIR / "reports"
    figures_dir = reports_dir / "figures"
    backend_data_dir = PROJECT_ROOT / "backend" / "app" / "data"
    figures_dir.mkdir(parents=True, exist_ok=True)
    backend_data_dir.mkdir(parents=True, exist_ok=True)

    clean_csv = data_dir / "aeroguard_clean_telemetry.csv"
    raw_csv = data_dir / "aeroguard_raw_telemetry.csv"
    extra_csv = data_dir / "aeroguard_lote_adicional_120000.csv"

    if clean_csv.exists():
        df_clean = pd.read_csv(clean_csv, low_memory=False)
    elif raw_csv.exists():
        df_clean, _ = clean_telemetry(pd.read_csv(raw_csv, low_memory=False))
        df_clean.to_csv(clean_csv, index=False)
    else:
        raise FileNotFoundError(f"No existe {clean_csv} ni {raw_csv}. Ejecuta 01_generate_dataset.py.")

    if len(df_clean) < 100000:
        raise ValueError(f"Se requieren >= 100,000 registros limpios, encontrados: {len(df_clean)}")

    print("=" * 80)
    print(" [AEROGUARD C-UAS] BENCHMARK PREDICTIVO DE 6 MODELOS (SIN DATA LEAKAGE)")
    print(f" Dataset principal limpio: {len(df_clean):,} registros")
    print("=" * 80)

    # Preparar lote 2 independiente si esta disponible
    df_lote2: pd.DataFrame | None = None
    if extra_csv.exists():
        df_lote2, _ = clean_telemetry(pd.read_csv(extra_csv, low_memory=False))
        print(f" Lote 2 independiente limpio: {len(df_lote2):,} registros")

    # Calcular targets sin usar threat_level como entrada
    df_clean["risk_score"] = compute_risk_score(df_clean, seed=42)
    df_clean["high_risk_binary"] = df_clean["threat_level"].isin(["HIGH", "CRITICAL"]).astype(int)

    for col in CATEGORICAL_FEATURES:
        df_clean[col] = df_clean[col].astype(str)

    if df_lote2 is not None:
        df_lote2["risk_score"] = compute_risk_score(df_lote2, seed=99)
        df_lote2["high_risk_binary"] = df_lote2["threat_level"].isin(["HIGH", "CRITICAL"]).astype(int)
        for col in CATEGORICAL_FEATURES:
            df_lote2[col] = df_lote2[col].astype(str)

    # Division estratificada UNICA previa a cualquier fit (80% train / 20% test)
    idx_all = np.arange(len(df_clean))
    train_idx, test_idx = train_test_split(
        idx_all, test_size=0.20, random_state=42, stratify=df_clean["threat_level"]
    )
    df_train = df_clean.iloc[train_idx].copy()
    df_test = df_clean.iloc[test_idx].copy()

    X_train = df_train[ALL_FEATURES]
    X_test = df_test[ALL_FEATURES]

    # =========================================================================
    # MODELO 1: REGRESION LINEAL (Puntaje continuo de riesgo cinematico 0-100)
    # =========================================================================
    print("\n>>> [1/6] Regresion Lineal (risk_score 0-100)...")
    lr_pipe = Pipeline(
        steps=[("preprocessor", _make_linear_preprocessor()), ("regressor", LinearRegression())]
    )
    lr_pipe.fit(X_train, df_train["risk_score"].to_numpy())
    y_pred_lr_test = np.clip(lr_pipe.predict(X_test), 0.0, 100.0)
    y_true_lr_test = df_test["risk_score"].to_numpy()

    lr_r2 = float(r2_score(y_true_lr_test, y_pred_lr_test))
    lr_mae = float(mean_absolute_error(y_true_lr_test, y_pred_lr_test))
    lr_rmse = float(root_mean_squared_error(y_true_lr_test, y_pred_lr_test))
    lr_metrics: dict[str, Any] = {
        "modelo": "Regresión Lineal (LinearRegression)",
        "pregunta_negocio": "¿Cuál es el puntaje continuo de riesgo cinemático (0–100) de un contacto según su telemetría?",
        "target": "risk_score",
        "test_r2": round(lr_r2, 4),
        "test_mae": round(lr_mae, 4),
        "test_rmse": round(lr_rmse, 4),
    }
    if df_lote2 is not None:
        yp_l2 = np.clip(lr_pipe.predict(df_lote2[ALL_FEATURES]), 0.0, 100.0)
        yt_l2 = df_lote2["risk_score"].to_numpy()
        lr_metrics["lote2_r2"] = round(float(r2_score(yt_l2, yp_l2)), 4)
        lr_metrics["lote2_mae"] = round(float(mean_absolute_error(yt_l2, yp_l2)), 4)
        lr_metrics["lote2_rmse"] = round(float(root_mean_squared_error(yt_l2, yp_l2)), 4)
    print(f"    Test R2={lr_r2:.4f} | MAE={lr_mae:.2f} | RMSE={lr_rmse:.2f}")

    # =========================================================================
    # MODELO 2: REGRESION LOGISTICA (Probabilidad de alto riesgo / violacion + umbral)
    # =========================================================================
    print("\n>>> [2/6] Regresion Logistica (probabilidad HIGH/CRITICAL y umbral optimo)...")
    # Sub-split interno en train para calibrar el umbral optimo sin tocar test
    sub_tr_idx, sub_val_idx = train_test_split(
        np.arange(len(df_train)),
        test_size=0.20,
        random_state=42,
        stratify=df_train["high_risk_binary"],
    )
    log_pipe_sub = Pipeline(
        steps=[("preprocessor", _make_linear_preprocessor()), ("classifier", LogisticRegression(max_iter=1000, random_state=42))]
    )
    log_pipe_sub.fit(X_train.iloc[sub_tr_idx], df_train["high_risk_binary"].iloc[sub_tr_idx].to_numpy())
    val_probs = log_pipe_sub.predict_proba(X_train.iloc[sub_val_idx])[:, 1]
    val_true = df_train["high_risk_binary"].iloc[sub_val_idx].to_numpy()

    best_thr = 0.50
    best_val_f1 = -1.0
    threshold_curve = []
    for thr in np.arange(0.25, 0.76, 0.05):
        thr_r = round(float(thr), 2)
        f1_v = float(f1_score(val_true, (val_probs >= thr_r).astype(int)))
        threshold_curve.append({"threshold": thr_r, "val_f1": round(f1_v, 4)})
        if f1_v > best_val_f1:
            best_val_f1 = f1_v
            best_thr = thr_r

    # Re-entrenar sobre todo X_train con los mismos hiperparametros
    log_pipe = Pipeline(
        steps=[("preprocessor", _make_linear_preprocessor()), ("classifier", LogisticRegression(max_iter=1000, random_state=42))]
    )
    log_pipe.fit(X_train, df_train["high_risk_binary"].to_numpy())
    y_prob_log_test = log_pipe.predict_proba(X_test)[:, 1]
    y_true_bin_test = df_test["high_risk_binary"].to_numpy()
    y_pred_log_opt = (y_prob_log_test >= best_thr).astype(int)
    y_pred_log_050 = (y_prob_log_test >= 0.50).astype(int)

    # Baseline multiclase (4 clases) de Regresion Logistica
    log_multi_pipe = Pipeline(
        steps=[("preprocessor", _make_linear_preprocessor()), ("classifier", LogisticRegression(max_iter=1000, random_state=42))]
    )
    log_multi_pipe.fit(X_train, df_train["threat_level"].to_numpy())
    y_pred_log_multi = log_multi_pipe.predict(X_test)

    log_auc = float(roc_auc_score(y_true_bin_test, y_prob_log_test))
    log_f1_opt = float(f1_score(y_true_bin_test, y_pred_log_opt))
    log_f1_050 = float(f1_score(y_true_bin_test, y_pred_log_050))
    log_prec_opt = float(precision_score(y_true_bin_test, y_pred_log_opt))
    log_rec_opt = float(recall_score(y_true_bin_test, y_pred_log_opt))
    log_acc_opt = float(accuracy_score(y_true_bin_test, y_pred_log_opt))
    log_brier = float(brier_score_loss(y_true_bin_test, y_prob_log_test))
    log_multi_acc = float(accuracy_score(df_test["threat_level"].to_numpy(), y_pred_log_multi))
    log_multi_f1 = float(f1_score(df_test["threat_level"].to_numpy(), y_pred_log_multi, average="weighted"))

    log_metrics: dict[str, Any] = {
        "modelo": "Regresión Logística (LogisticRegression)",
        "pregunta_negocio": "¿Cuál es la probabilidad de violación crítica / alto riesgo de geocerca y qué umbral optimiza el F1?",
        "target_binario": "high_risk_binary (HIGH | CRITICAL)",
        "optimal_threshold": best_thr,
        "test_roc_auc": round(log_auc, 4),
        "test_f1_optimal": round(log_f1_opt, 4),
        "test_f1_050": round(log_f1_050, 4),
        "test_precision_optimal": round(log_prec_opt, 4),
        "test_recall_optimal": round(log_rec_opt, 4),
        "test_accuracy_optimal": round(log_acc_opt, 4),
        "test_brier_score": round(log_brier, 4),
        "multiclass_baseline_accuracy": round(log_multi_acc, 4),
        "multiclass_baseline_f1_weighted": round(log_multi_f1, 4),
    }
    if df_lote2 is not None:
        yp_bin_l2 = log_pipe.predict_proba(df_lote2[ALL_FEATURES])[:, 1]
        yt_bin_l2 = df_lote2["high_risk_binary"].to_numpy()
        log_metrics["lote2_roc_auc"] = round(float(roc_auc_score(yt_bin_l2, yp_bin_l2)), 4)
        log_metrics["lote2_f1_optimal"] = round(float(f1_score(yt_bin_l2, (yp_bin_l2 >= best_thr).astype(int))), 4)
        log_metrics["lote2_multiclass_accuracy"] = round(
            float(accuracy_score(df_lote2["threat_level"].to_numpy(), log_multi_pipe.predict(df_lote2[ALL_FEATURES]))), 4
        )
    print(f"    ROC-AUC={log_auc:.4f} | Umbral={best_thr:.2f} | F1={log_f1_opt:.4f} | Baseline 4-clases Acc={log_multi_acc*100:.2f}%")

    # =========================================================================
    # MODELO 3: K-MEANS (Agrupamiento no supervisado de perfiles de vuelo)
    # =========================================================================
    print("\n>>> [3/6] K-Means (perfiles no supervisados de vuelo)...")
    km_scaler = StandardScaler()
    X_km_train = km_scaler.fit_transform(df_train[KMEANS_FEATURES].to_numpy())
    X_km_test = km_scaler.transform(df_test[KMEANS_FEATURES].to_numpy())

    # Muestra estratificada del conjunto de prueba para Silhouette rapido y estable
    _, sil_sample_idx = train_test_split(
        np.arange(len(X_km_test)), test_size=min(10000, len(X_km_test)), random_state=42, stratify=df_test["threat_level"]
    )
    X_sil = X_km_test[sil_sample_idx]

    elbow_results = []
    for k in range(2, 9):
        km_k = KMeans(n_clusters=k, n_init=10, random_state=42)
        km_k.fit(X_km_train)
        sil_k = float(silhouette_score(X_sil, km_k.predict(X_sil)))
        elbow_results.append({"k": k, "inertia": round(float(km_k.inertia_), 1), "silhouette": round(sil_k, 4)})
        print(f"    k={k}: Inertia={km_k.inertia_:,.1f} | Silhouette={sil_k:.4f}")

    chosen_k = 4
    km_final = KMeans(n_clusters=chosen_k, n_init=10, random_state=42)
    km_final.fit(X_km_train)
    test_clusters = km_final.predict(X_km_test)
    sil_chosen = next(r["silhouette"] for r in elbow_results if r["k"] == chosen_k)
    best_sil_entry = max(elbow_results, key=lambda r: r["silhouette"])

    centroids_phys_arr = km_scaler.inverse_transform(km_final.cluster_centers_)
    centroids_phys_df = pd.DataFrame(centroids_phys_arr, columns=KMEANS_FEATURES)
    hr_rates = [
        float(df_test.loc[test_clusters == c, "high_risk_binary"].mean() * 100.0)
        for c in range(chosen_k)
    ]
    cluster_profiles = _label_kmeans_clusters(centroids_phys_df, hr_rates)
    for prof in cluster_profiles:
        cid = prof["cluster_id"]
        prof["test_count"] = int((test_clusters == cid).sum())
        prof["test_pct"] = round(float((test_clusters == cid).mean() * 100.0), 2)

    km_metrics: dict[str, Any] = {
        "modelo": "K-Means (Clustering No Supervisado)",
        "pregunta_negocio": "¿Qué perfiles operativos de vuelo existen sin etiquetas previas en el espacio aéreo?",
        "selected_k": chosen_k,
        "inertia_k4": round(float(km_final.inertia_), 1),
        "silhouette_k4": sil_chosen,
        "max_silhouette_k": best_sil_entry["k"],
        "max_silhouette_score": best_sil_entry["silhouette"],
        "elbow_curve": elbow_results,
        "cluster_profiles": cluster_profiles,
    }

    # =========================================================================
    # MODELO 4 y 5: ARBOL DE DECISION Y RANDOM FOREST (threat_level 4 clases)
    # =========================================================================
    print("\n>>> [4/6] Arbol de Decision (DecisionTreeClassifier, max_depth=12)...")
    dt_pipe = Pipeline(
        steps=[
            ("preprocessor", _make_tree_preprocessor()),
            ("classifier", DecisionTreeClassifier(max_depth=12, min_samples_split=10, min_samples_leaf=5, random_state=42)),
        ]
    )
    dt_pipe.fit(X_train, df_train["threat_level"].to_numpy())
    y_pred_dt = dt_pipe.predict(X_test)
    y_true_cls = df_test["threat_level"].to_numpy()

    dt_acc = float(accuracy_score(y_true_cls, y_pred_dt))
    dt_f1_w = float(f1_score(y_true_cls, y_pred_dt, average="weighted"))
    dt_f1_m = float(f1_score(y_true_cls, y_pred_dt, average="macro"))
    dt_metrics: dict[str, Any] = {
        "modelo": "Árbol de Decisión (DecisionTreeClassifier)",
        "pregunta_negocio": "¿Qué reglas jerárquicas interpretables clasifican el nivel de amenaza (LOW/MEDIUM/HIGH/CRITICAL)?",
        "test_accuracy": round(dt_acc, 4),
        "test_precision_weighted": round(float(precision_score(y_true_cls, y_pred_dt, average="weighted")), 4),
        "test_recall_weighted": round(float(recall_score(y_true_cls, y_pred_dt, average="weighted")), 4),
        "test_f1_weighted": round(dt_f1_w, 4),
        "test_f1_macro": round(dt_f1_m, 4),
    }

    print("\n>>> [5/6] Random Forest (100 arboles completo + 12 arboles compacto para runtime Oracle)...")
    rf_full_pipe = Pipeline(
        steps=[
            ("preprocessor", _make_tree_preprocessor()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=100,
                    max_depth=16,
                    max_features=0.75,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    rf_full_pipe.fit(X_train, df_train["threat_level"].to_numpy())
    y_pred_rf_full = rf_full_pipe.predict(X_test)

    rf_compact_pipe = Pipeline(
        steps=[
            ("preprocessor", _make_tree_preprocessor()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=12,
                    max_depth=13,
                    max_features=0.75,
                    min_samples_leaf=15,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    rf_compact_pipe.fit(X_train, df_train["threat_level"].to_numpy())
    y_pred_rf_compact = rf_compact_pipe.predict(X_test)

    rf_acc = float(accuracy_score(y_true_cls, y_pred_rf_full))
    rf_f1_w = float(f1_score(y_true_cls, y_pred_rf_full, average="weighted"))
    rf_f1_m = float(f1_score(y_true_cls, y_pred_rf_full, average="macro"))
    rf_compact_acc = float(accuracy_score(y_true_cls, y_pred_rf_compact))
    rf_compact_f1_w = float(f1_score(y_true_cls, y_pred_rf_compact, average="weighted"))
    acc_diff_pp = (rf_compact_acc - rf_acc) * 100.0
    assert (rf_acc - rf_compact_acc) * 100.0 <= 1.0, (
        f"RF compacto pierde demasiada exactitud ({acc_diff_pp:.2f} pp)"
    )

    rf_metrics: dict[str, Any] = {
        "modelo": "Random Forest (RandomForestClassifier)",
        "pregunta_negocio": "¿Qué ensamble logra la clasificación multiclase de threat_level más estable para producción?",
        "test_accuracy": round(rf_acc, 4),
        "test_precision_weighted": round(float(precision_score(y_true_cls, y_pred_rf_full, average="weighted")), 4),
        "test_recall_weighted": round(float(recall_score(y_true_cls, y_pred_rf_full, average="weighted")), 4),
        "test_f1_weighted": round(rf_f1_w, 4),
        "test_f1_macro": round(rf_f1_m, 4),
        "runtime_compact_accuracy": round(rf_compact_acc, 4),
        "runtime_compact_f1_weighted": round(rf_compact_f1_w, 4),
        "runtime_accuracy_diff_pp": round((rf_compact_acc - rf_acc) * 100.0, 3),
    }
    if df_lote2 is not None:
        yt_cls_l2 = df_lote2["threat_level"].to_numpy()
        dt_l2 = dt_pipe.predict(df_lote2[ALL_FEATURES])
        rf_l2 = rf_full_pipe.predict(df_lote2[ALL_FEATURES])
        rfc_l2 = rf_compact_pipe.predict(df_lote2[ALL_FEATURES])
        dt_metrics["lote2_accuracy"] = round(float(accuracy_score(yt_cls_l2, dt_l2)), 4)
        dt_metrics["lote2_f1_weighted"] = round(float(f1_score(yt_cls_l2, dt_l2, average="weighted")), 4)
        rf_metrics["lote2_accuracy"] = round(float(accuracy_score(yt_cls_l2, rf_l2)), 4)
        rf_metrics["lote2_f1_weighted"] = round(float(f1_score(yt_cls_l2, rf_l2, average="weighted")), 4)
        rf_metrics["lote2_runtime_compact_accuracy"] = round(float(accuracy_score(yt_cls_l2, rfc_l2)), 4)

    print(f"    Decision Tree   -> Test Acc={dt_acc*100:.2f}% | F1(W)={dt_f1_w:.4f}")
    print(f"    Random Forest   -> Test Acc={rf_acc*100:.2f}% | F1(W)={rf_f1_w:.4f}")
    print(f"    RF Compacto(12) -> Test Acc={rf_compact_acc*100:.2f}% | F1(W)={rf_compact_f1_w:.4f} (diff={acc_diff_pp:+.2f} pp)")

    # =========================================================================
    # MODELO 6: ARIMA (Pronostico diario de incursiones HIGH/CRITICAL)
    # =========================================================================
    print("\n>>> [6/6] ARIMA (serie temporal diaria de incursiones HIGH/CRITICAL)...")
    ts_df = df_clean[["timestamp", "high_risk_binary"]].copy()
    ts_df["date"] = pd.to_datetime(ts_df["timestamp"], errors="coerce").dt.floor("D")
    ts_df = ts_df.dropna(subset=["date"])
    daily = (
        ts_df.groupby("date")
        .agg(total_detections=("high_risk_binary", "size"), high_risk_count=("high_risk_binary", "sum"))
        .sort_index()
    )
    full_idx = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(full_idx, fill_value=0)
    daily.index.name = "date"

    series = daily["high_risk_count"].astype(float)
    split_pos = int(len(series) * 0.80)
    ts_train = series.iloc[:split_pos]
    ts_test = series.iloc[split_pos:]

    candidate_orders = [(1, 0, 1), (2, 0, 1), (1, 1, 1), (2, 1, 1), (3, 0, 2)]
    best_order = (1, 0, 1)
    best_aic = float("inf")
    order_evaluations = []
    for order in candidate_orders:
        try:
            fitted = ARIMA(ts_train, order=order).fit()
            aic_val = float(fitted.aic)
            order_evaluations.append({"order": list(order), "aic": round(aic_val, 2)})
            if aic_val < best_aic:
                best_aic = aic_val
                best_order = order
        except Exception:
            continue

    arima_train_fit = ARIMA(ts_train, order=best_order).fit()
    arima_test_pred = arima_train_fit.forecast(steps=len(ts_test))
    y_ts_true = ts_test.to_numpy()
    y_ts_pred = np.asarray(arima_test_pred, dtype=float)

    arima_mae = float(mean_absolute_error(y_ts_true, y_ts_pred))
    arima_rmse = float(root_mean_squared_error(y_ts_true, y_ts_pred))
    nonzero = np.where(y_ts_true == 0, 1.0, y_ts_true)
    arima_mape = float(np.mean(np.abs((y_ts_true - y_ts_pred) / nonzero)) * 100.0)

    # Reajustar con serie completa para pronostico de los proximos 14 dias
    arima_full_fit = ARIMA(series, order=best_order).fit()
    fc_obj = arima_full_fit.get_forecast(steps=14)
    fc_mean = fc_obj.predicted_mean
    fc_ci = fc_obj.conf_int(alpha=0.05)

    forecast_14d = []
    for step_i, dt_val in enumerate(fc_mean.index):
        forecast_14d.append(
            {
                "date": dt_val.strftime("%Y-%m-%d"),
                "predicted_high_risk": round(float(max(0.0, fc_mean.iloc[step_i])), 2),
                "lower_95": round(float(max(0.0, fc_ci.iloc[step_i, 0])), 2),
                "upper_95": round(float(max(0.0, fc_ci.iloc[step_i, 1])), 2),
            }
        )
    recent_history = [
        {
            "date": idx.strftime("%Y-%m-%d"),
            "total_detections": int(daily.loc[idx, "total_detections"]),
            "high_risk_count": int(daily.loc[idx, "high_risk_count"]),
        }
        for idx in daily.index[-30:]
    ]
    peak_day = max(forecast_14d, key=lambda x: x["predicted_high_risk"])

    arima_metrics: dict[str, Any] = {
        "modelo": f"ARIMA{best_order}",
        "pregunta_negocio": "¿Cuántas incursiones diarias de alto riesgo (HIGH/CRITICAL) se pronostican en las próximas 2 semanas?",
        "order": list(best_order),
        "days_total": int(len(series)),
        "days_train": int(len(ts_train)),
        "days_test": int(len(ts_test)),
        "aic": round(best_aic, 2),
        "test_mae": round(arima_mae, 3),
        "test_rmse": round(arima_rmse, 3),
        "test_mape_pct": round(arima_mape, 2),
        "candidates": order_evaluations,
        "peak_forecast_14d": peak_day,
    }
    print(f"    ARIMA{best_order} -> AIC={best_aic:.2f} | Test MAE={arima_mae:.2f} | RMSE={arima_rmse:.2f} | MAPE={arima_mape:.2f}%")

    # =========================================================================
    # VERIFICACION DE EQUIVALENCIA PARIDAD PURE-JSON VS SKLEARN (RUNTIME ORACLE)
    # =========================================================================
    tree_pre = rf_compact_pipe.named_steps["preprocessor"]
    tree_clf = rf_compact_pipe.named_steps["classifier"]
    rf_classes = [str(c) for c in tree_clf.classes_.tolist()]
    exported_trees = [_export_tree(est) for est in tree_clf.estimators_]

    X_test_transformed = tree_pre.transform(X_test)
    sklearn_probs = tree_clf.predict_proba(X_test_transformed[:1000])
    sklearn_preds = [rf_classes[int(i)] for i in np.argmax(sklearn_probs, axis=1)]

    parity_matches = 0
    max_prob_diff = 0.0
    for i in range(1000):
        p_cls, p_vec = _predict_exported_rf(X_test_transformed[i], exported_trees, rf_classes)
        if p_cls == sklearn_preds[i]:
            parity_matches += 1
        max_prob_diff = max(max_prob_diff, float(np.max(np.abs(p_vec - sklearn_probs[i]))))

    parity_rate = parity_matches / 1000.0
    assert parity_rate >= 0.999, f"Paridad RF JSON insuficiente: {parity_rate:.4f}"
    print(f"\n -> [OK] Paridad inferencia JSON vs scikit-learn: {parity_rate*100:.2f}% (diff max={max_prob_diff:.5f})")

    # =========================================================================
    # EXPORTACION DEL ARTEFACTO LIVIANO PARA FASTAPI + COMPARATIVA JSON
    # =========================================================================
    lin_pre = lr_pipe.named_steps["preprocessor"]
    lin_num_scaler = lin_pre.named_transformers_["num"]
    lin_cat_ohe = lin_pre.named_transformers_["cat"]
    lr_est = lr_pipe.named_steps["regressor"]
    log_est = log_pipe.named_steps["classifier"]
    tree_num_scaler = tree_pre.named_transformers_["num"]
    tree_cat_enc = tree_pre.named_transformers_["cat"]

    artifact = {
        "version": "1.2.0-predictive-6models",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_origin": "synthetic_crisp_dm_dataset",
        "dataset_stats": {
            "raw_records": 125000,
            "clean_records": int(len(df_clean)),
            "train_records": int(len(df_train)),
            "test_records": int(len(df_test)),
            "lote2_clean_records": int(len(df_lote2)) if df_lote2 is not None else 0,
        },
        "linear_logistic_preprocessor": {
            "numeric_features": NUMERIC_FEATURES,
            "scaler_mean": [float(v) for v in lin_num_scaler.mean_.tolist()],
            "scaler_scale": [float(v) for v in lin_num_scaler.scale_.tolist()],
            "categorical_features": CATEGORICAL_FEATURES,
            "categorical_categories": [[str(x) for x in cats] for cats in lin_cat_ohe.categories_],
        },
        "linear_regression": {
            "coef": [float(v) for v in lr_est.coef_.tolist()],
            "intercept": float(lr_est.intercept_),
            "metrics": lr_metrics,
        },
        "logistic_regression": {
            "coef": [float(v) for v in log_est.coef_[0].tolist()],
            "intercept": float(log_est.intercept_[0]),
            "optimal_threshold": best_thr,
            "metrics": log_metrics,
        },
        "kmeans": {
            "features": KMEANS_FEATURES,
            "scaler_mean": [float(v) for v in km_scaler.mean_.tolist()],
            "scaler_scale": [float(v) for v in km_scaler.scale_.tolist()],
            "centroids_scaled": [[float(x) for x in row] for row in km_final.cluster_centers_.tolist()],
            "profiles": cluster_profiles,
            "metrics": km_metrics,
        },
        "decision_tree": {
            "metrics": dt_metrics,
        },
        "random_forest": {
            "numeric_features": NUMERIC_FEATURES,
            "scaler_mean": [float(v) for v in tree_num_scaler.mean_.tolist()],
            "scaler_scale": [float(v) for v in tree_num_scaler.scale_.tolist()],
            "categorical_features": CATEGORICAL_FEATURES,
            "categorical_categories": [[str(x) for x in cats] for cats in tree_cat_enc.categories_],
            "classes": rf_classes,
            "trees": exported_trees,
            "metrics": rf_metrics,
        },
        "arima": {
            "metrics": arima_metrics,
            "recent_history_30d": recent_history,
            "forecast_14d": forecast_14d,
        },
        "production_decision": {
            "primary_classifier": f"Random Forest (compacto 12 árboles en runtime: {rf_compact_acc*100:.2f}% Acc, F1={rf_compact_f1_w:.4f})",
            "interpretable_companion": "Árbol de Decisión (reglas auditables)",
            "continuous_risk_model": "Regresión Lineal (risk_score 0-100)",
            "probability_breach_model": f"Regresión Logística binaria (umbral óptimo={best_thr:.2f}, ROC-AUC={log_auc:.4f})",
            "unsupervised_profiling": f"K-Means (k={chosen_k}, Silhouette={sil_chosen:.4f})",
            "time_series_forecast": f"ARIMA{best_order} (horizonte 14 días, MAPE={arima_mape:.2f}%)",
        },
    }

    artifact_path = backend_data_dir / "predictive_models_artifact.json"
    with open(artifact_path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, ensure_ascii=False, separators=(",", ":"))
    artifact_kb = artifact_path.stat().st_size / 1024.0
    print(f" -> Artefacto runtime guardado: {artifact_path} ({artifact_kb:.1f} KB)")
    assert artifact_kb < 1536.0, f"Artefacto excede 1.5 MB: {artifact_kb:.1f} KB"

    report_payload = {
        "generated_at_utc": artifact["generated_at_utc"],
        "dataset_stats": artifact["dataset_stats"],
        "models": {
            "1_regresion_lineal": lr_metrics,
            "2_regresion_logistica": log_metrics,
            "3_kmeans": km_metrics,
            "4_arbol_decision": dt_metrics,
            "5_random_forest": rf_metrics,
            "6_arima": arima_metrics,
        },
        "threshold_sweep": threshold_curve,
        "runtime_artifact_kb": round(artifact_kb, 1),
        "runtime_rf_parity_pct": round(parity_rate * 100.0, 2),
        "production_decision": artifact["production_decision"],
    }
    comp_path = reports_dir / "comparativa_6_modelos.json"
    with open(comp_path, "w", encoding="utf-8") as fh:
        json.dump(report_payload, fh, ensure_ascii=False, indent=2)
    print(f" -> Comparativa guardada: {comp_path}")

    # =========================================================================
    # GRAFICAS DE EVIDENCIA (300 DPI)
    # =========================================================================
    # FIGURA 07: Regresion Lineal + Curva ROC Regresion Logistica
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    sample_lr = np.random.default_rng(42).choice(len(y_true_lr_test), size=min(3000, len(y_true_lr_test)), replace=False)
    axes[0].scatter(y_true_lr_test[sample_lr], y_pred_lr_test[sample_lr], alpha=0.25, s=12, color="#2980b9")
    axes[0].plot([0, 100], [0, 100], "r--", linewidth=1.8, label="Identidad ideal (y = x)")
    axes[0].set_title(f"1. Regresión Lineal: Risk Score (0–100)\nR² = {lr_r2:.4f} | MAE = {lr_mae:.2f} | RMSE = {lr_rmse:.2f}", fontweight="bold")
    axes[0].set_xlabel("Risk Score Real (sintético)")
    axes[0].set_ylabel("Risk Score Predicho")
    axes[0].legend()

    fpr, tpr, _ = roc_curve(y_true_bin_test, y_prob_log_test)
    axes[1].plot(fpr, tpr, color="#27ae60", linewidth=2.2, label=f"ROC (AUC = {log_auc:.4f})")
    axes[1].plot([0, 1], [0, 1], "k--", alpha=0.5, label="Azar (AUC = 0.50)")
    axes[1].set_title(f"2. Regresión Logística: Alto Riesgo / Geocerca\nUmbral óptimo = {best_thr:.2f} | F1 = {log_f1_opt:.4f}", fontweight="bold")
    axes[1].set_xlabel("Tasa de Falsos Positivos (FPR)")
    axes[1].set_ylabel("Tasa de Verdaderos Positivos (TPR)")
    axes[1].legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(figures_dir / "07_regresion_lineal_y_logistica.png", dpi=300, bbox_inches="tight")
    plt.close()

    # FIGURA 08: K-Means Codo, Silhouette y Perfiles
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    ks = [r["k"] for r in elbow_results]
    inertias = [r["inertia"] / 1000.0 for r in elbow_results]
    sils = [r["silhouette"] for r in elbow_results]
    ax_sil = axes[0].twinx()
    l1 = axes[0].plot(ks, inertias, "o-", color="#2c3e50", linewidth=2, label="Inercia (x1000)")
    l2 = ax_sil.plot(ks, sils, "s--", color="#e67e22", linewidth=2, label="Silhouette Score")
    axes[0].axvline(chosen_k, color="#e74c3c", linestyle=":", linewidth=1.8, label=f"k seleccionado = {chosen_k}")
    axes[0].set_title("3. K-Means: Método del Codo y Silhouette Score", fontweight="bold")
    axes[0].set_xlabel("Número de clústeres (k)")
    axes[0].set_ylabel("Inercia (miles)")
    ax_sil.set_ylabel("Silhouette Score")
    lines = l1 + l2
    axes[0].legend(lines, [l.get_label() for l in lines], loc="upper right")

    prof_names = [f"C{p['cluster_id']}: {p['label'][:24]}" for p in cluster_profiles]
    prof_hr = [p["high_risk_rate_pct"] for p in cluster_profiles]
    bars = axes[1].barh(prof_names, prof_hr, color=["#e74c3c", "#f39c12", "#3498db", "#2ecc71"][: len(prof_names)])
    axes[1].set_title("Perfiles K-Means (k=4): Tasa de Alto Riesgo (%)", fontweight="bold")
    axes[1].set_xlabel("% Eventos HIGH / CRITICAL en el clúster")
    for bar in bars:
        w = bar.get_width()
        axes[1].text(w + 1.0, bar.get_y() + bar.get_height() / 2, f"{w:.1f}%", va="center", fontweight="bold", fontsize=9)
    plt.tight_layout()
    plt.savefig(figures_dir / "08_kmeans_codo_y_perfiles.png", dpi=300, bbox_inches="tight")
    plt.close()

    # FIGURA 09: ARIMA Serie historica, Test y Pronostico 14 dias
    fig, ax = plt.subplots(figsize=(14, 5.5))
    ax.plot(ts_train.index[-60:], ts_train.values[-60:], label="Entrenamiento (últimos 60d)", color="#34495e", linewidth=1.5)
    ax.plot(ts_test.index, y_ts_true, label="Prueba real (20% cronológico)", color="#2980b9", linewidth=1.6)
    ax.plot(ts_test.index, y_ts_pred, label=f"Predicción ARIMA{best_order} en Test", color="#e67e22", linestyle="--", linewidth=1.8)
    fc_dates = pd.to_datetime([d["date"] for d in forecast_14d])
    fc_vals = [d["predicted_high_risk"] for d in forecast_14d]
    fc_lo = [d["lower_95"] for d in forecast_14d]
    fc_hi = [d["upper_95"] for d in forecast_14d]
    ax.plot(fc_dates, fc_vals, label="Pronóstico futuro (14 días)", color="#e74c3c", marker="o", markersize=4, linewidth=2)
    ax.fill_between(fc_dates, fc_lo, fc_hi, color="#e74c3c", alpha=0.18, label="Intervalo de confianza 95%")
    ax.set_title(f"6. ARIMA{best_order}: Pronóstico Diario de Incursiones HIGH/CRITICAL\nTest MAE={arima_mae:.2f} | RMSE={arima_rmse:.2f} | MAPE={arima_mape:.2f}% | AIC={best_aic:.1f}", fontweight="bold")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Incursiones diarias de alto riesgo")
    ax.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig(figures_dir / "09_arima_pronostico_incursiones.png", dpi=300, bbox_inches="tight")
    plt.close()

    # FIGURA 10: Comparativa resumen de clasificadores y metrica principal de los 6 modelos
    fig, ax = plt.subplots(figsize=(11, 5.5))
    comp_labels = [
        "Random Forest (100)\n[threat_level Acc]",
        "RF Runtime (12)\n[threat_level Acc]",
        "Árbol Decisión\n[threat_level Acc]",
        "Reg. Logística\n[Binaria F1/AUC]",
        "Reg. Logística\n[4-clases Acc]",
        "Regresión Lineal\n[risk_score R²]",
    ]
    comp_values = [rf_acc * 100, rf_compact_acc * 100, dt_acc * 100, log_f1_opt * 100, log_multi_acc * 100, lr_r2 * 100]
    bar_colors = ["#1abc9c", "#16a085", "#3498db", "#9b59b6", "#95a5a6", "#f39c12"]
    bars = ax.barh(comp_labels[::-1], comp_values[::-1], color=bar_colors[::-1], edgecolor="#2c3e50")
    ax.axvline(92.0, color="#e74c3c", linestyle="--", linewidth=1.5, label="Meta de clasificación C-UAS (92%)")
    ax.set_xlim(0, 108)
    ax.set_xlabel("Desempeño (%)", fontweight="bold")
    ax.set_title("Resumen Comparativo de Desempeño Predictivo (AeroGuard CRISP-DM)", fontweight="bold")
    for b in bars:
        w = b.get_width()
        ax.text(w + 1.0, b.get_y() + b.get_height() / 2, f"{w:.2f}%", va="center", fontweight="bold", fontsize=9)
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(figures_dir / "10_comparativa_6_modelos_resumen.png", dpi=300, bbox_inches="tight")
    plt.close()

    print(" -> [OK] 4 graficas generadas en data_mining/reports/figures/ (07 a 10)")
    print("=" * 80)
    return report_payload


if __name__ == "__main__":
    run_benchmark()
