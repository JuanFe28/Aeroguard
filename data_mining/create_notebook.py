#!/usr/bin/env python3
"""
Generador del Jupyter Notebook interactivo CRISP_DM_AeroGuard.ipynb
Estructurado en las 6 fases de la metodologia CRISP-DM (sin data leakage,
comparativa de 6 modelos predictivos, reglas calculadas y artefacto runtime).
"""

import json
import os


def build_notebook():
    nb = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# Minería de Datos Predictiva (CRISP-DM) — AeroGuard C-UAS\n",
                    "## Evaluación Comparativa de 6 Modelos y Despliegue en Producción\n",
                    "\n",
                    "**Equipo:** AeroGuard — Unidades Tecnológicas de Santander (UTS)\n",
                    "**Datasets:** 125,000 registros brutos $\\rightarrow$ **108,750 limpios** + **Lote 2 independiente (104,400 limpios)**\n",
                    "**Nota metodológica:** Datos sintéticos para validación académica; las métricas comprueban consistencia sobre el generador y no desempeño en sensores físicos."
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "---\n",
                    "## Fase 1: Comprensión del Negocio (Business Understanding)\n",
                    "\n",
                    "Cada algoritmo responde a una pregunta predictiva concreta en AeroGuard:\n",
                    "1. **Regresión Lineal:** ¿Cuál es el puntaje continuo de riesgo cinemático (`risk_score`, 0–100)?\n",
                    "2. **Regresión Logística:** ¿Cuál es la probabilidad de violación / alto riesgo de geocerca (`HIGH`/`CRITICAL`) y qué umbral optimiza el F1?\n",
                    "3. **K-Means:** ¿Qué perfiles operativos de vuelo emergen sin etiquetas previas?\n",
                    "4. **Árbol de Decisión:** ¿Qué reglas jerárquicas auditables clasifican `threat_level`?\n",
                    "5. **Random Forest:** ¿Qué ensamble logra la clasificación más robusta para operar en tiempo real?\n",
                    "6. **ARIMA:** ¿Cuántas incursiones diarias de alto riesgo se pronostican en los próximos 14 días?"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "import os, sys, json\n",
                    "import numpy as np\n",
                    "import pandas as pd\n",
                    "import matplotlib.pyplot as plt\n",
                    "import seaborn as sns\n",
                    "from sklearn.model_selection import train_test_split\n",
                    "from sklearn.compose import ColumnTransformer\n",
                    "from sklearn.pipeline import Pipeline\n",
                    "from sklearn.preprocessing import StandardScaler, OneHotEncoder, OrdinalEncoder\n",
                    "from sklearn.linear_model import LinearRegression, LogisticRegression\n",
                    "from sklearn.cluster import KMeans\n",
                    "from sklearn.tree import DecisionTreeClassifier\n",
                    "from sklearn.ensemble import RandomForestClassifier\n",
                    "from sklearn.metrics import (\n",
                    "    r2_score, mean_absolute_error, root_mean_squared_error,\n",
                    "    roc_auc_score, f1_score, accuracy_score, confusion_matrix, silhouette_score\n",
                    ")\n",
                    "from statsmodels.tsa.arima.model import ARIMA\n",
                    "\n",
                    "dm_dir = 'data_mining' if os.path.exists('data_mining/limpieza.py') else '.'\n",
                    "if dm_dir not in sys.path:\n",
                    "    sys.path.insert(0, dm_dir)\n",
                    "from limpieza import clean_telemetry, compute_risk_score\n",
                    "\n",
                    "sns.set_theme(style='whitegrid', palette='muted')\n",
                    "print('Entorno CRISP-DM predictivo (6 modelos) cargado correctamente.')"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "---\n",
                    "## Fase 2 y 3: Comprensión, Limpieza Compartida y Control de Data Leakage\n",
                    "\n",
                    "El pipeline aplica `clean_telemetry()` (deduplicación, normalización de tokens corruptos, rangos válidos e imputación por mediana/moda) y separa **Entrenamiento (80%) / Prueba (20%)** **antes** de ajustar escaladores y codificadores (`ColumnTransformer`)."
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "raw_path = os.path.join(dm_dir, 'data', 'aeroguard_raw_telemetry.csv')\n",
                    "df_raw = pd.read_csv(raw_path, low_memory=False)\n",
                    "df_clean, resumen = clean_telemetry(df_raw)\n",
                    "df_clean['risk_score'] = compute_risk_score(df_clean, seed=42)\n",
                    "df_clean['high_risk_binary'] = df_clean['threat_level'].isin(['HIGH', 'CRITICAL']).astype(int)\n",
                    "print(f\"Brutos: {resumen['registros_brutos']:,} | Duplicados: {resumen['duplicados_eliminados']:,} | Anomalías: {resumen['filas_fuera_de_rango_fisico']:,} | Limpios: {resumen['registros_limpios']:,}\")\n",
                    "\n",
                    "fig, axes = plt.subplots(1, 2, figsize=(13, 4))\n",
                    "sns.boxplot(y=pd.to_numeric(df_raw['altitude_m'], errors='coerce'), ax=axes[0], color='#e74c3c')\n",
                    "axes[0].set_title('Antes: Altitud Bruta (Outliers > 3,500 m)')\n",
                    "sns.boxplot(y=df_clean['altitude_m'], ax=axes[1], color='#2ecc71')\n",
                    "axes[1].set_title(f\"Después: Altitud Limpia (n={len(df_clean):,})\")\n",
                    "plt.tight_layout()\n",
                    "plt.show()"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "---\n",
                    "## Fases 4 y 5: Modelado y Evaluación Comparativa de los 6 Algoritmos (Sin Data Leakage)"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "NUM = ['altitude_m','speed_ms','vertical_speed_ms','heading_deg','distance_to_zone_m','rf_signal_dbm','battery_est_pct','ai_confidence','wind_speed_kmh']\n",
                    "CAT = ['drone_class','flight_pattern','weather_condition','city_zone']\n",
                    "for c in CAT:\n",
                    "    df_clean[c] = df_clean[c].astype(str)\n",
                    "\n",
                    "df_train, df_test = train_test_split(df_clean, test_size=0.20, random_state=42, stratify=df_clean['threat_level'])\n",
                    "X_tr, X_te = df_train[NUM + CAT], df_test[NUM + CAT]\n",
                    "print(f'Train: {len(X_tr):,} | Test: {len(X_te):,} (split previo al fit)')\n",
                    "\n",
                    "def lin_pre():\n",
                    "    return ColumnTransformer([('num', StandardScaler(), NUM), ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), CAT)])\n",
                    "\n",
                    "def tree_pre():\n",
                    "    return ColumnTransformer([('num', StandardScaler(), NUM), ('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1), CAT)])\n",
                    "\n",
                    "# 1. Regresion Lineal\n",
                    "lr = Pipeline([('pre', lin_pre()), ('m', LinearRegression())]).fit(X_tr, df_train['risk_score'])\n",
                    "lr_pred = np.clip(lr.predict(X_te), 0, 100)\n",
                    "print(f'[1] Regresión Lineal   -> R²={r2_score(df_test[\"risk_score\"], lr_pred):.4f} | MAE={mean_absolute_error(df_test[\"risk_score\"], lr_pred):.2f} | RMSE={root_mean_squared_error(df_test[\"risk_score\"], lr_pred):.2f}')\n",
                    "\n",
                    "# 2. Regresion Logistica (Binaria HIGH/CRITICAL)\n",
                    "log_bin = Pipeline([('pre', lin_pre()), ('m', LogisticRegression(max_iter=1000, random_state=42))]).fit(X_tr, df_train['high_risk_binary'])\n",
                    "log_prob = log_bin.predict_proba(X_te)[:, 1]\n",
                    "print(f'[2] Regresión Logística -> ROC-AUC={roc_auc_score(df_test[\"high_risk_binary\"], log_prob):.4f} | F1(umbral=0.40)={f1_score(df_test[\"high_risk_binary\"], (log_prob>=0.40).astype(int)):.4f}')\n",
                    "\n",
                    "# 3. K-Means (k=4, 3 variables cinematicas clave)\n",
                    "KM_COLS = ['distance_to_zone_m', 'altitude_m', 'speed_ms']\n",
                    "km_sc = StandardScaler().fit(df_train[KM_COLS].to_numpy())\n",
                    "km = KMeans(n_clusters=4, n_init=10, random_state=42).fit(km_sc.transform(df_train[KM_COLS].to_numpy()))\n",
                    "X_km_te = km_sc.transform(df_test[KM_COLS].to_numpy())\n",
                    "sil = silhouette_score(X_km_te[:10000], km.predict(X_km_te[:10000]))\n",
                    "print(f'[3] K-Means (k=4)      -> Inertia={km.inertia_:,.1f} | Silhouette={sil:.4f}')\n",
                    "\n",
                    "# 4. Arbol de Decision y 5. Random Forest (Completo 100 y Runtime Compacto 12)\n",
                    "dt = Pipeline([('pre', tree_pre()), ('m', DecisionTreeClassifier(max_depth=12, min_samples_split=10, min_samples_leaf=5, random_state=42))]).fit(X_tr, df_train['threat_level'])\n",
                    "rf = Pipeline([('pre', tree_pre()), ('m', RandomForestClassifier(n_estimators=100, max_depth=16, max_features=0.75, min_samples_split=5, min_samples_leaf=2, random_state=42, n_jobs=-1))]).fit(X_tr, df_train['threat_level'])\n",
                    "rf_c = Pipeline([('pre', tree_pre()), ('m', RandomForestClassifier(n_estimators=12, max_depth=13, max_features=0.75, min_samples_leaf=15, random_state=42, n_jobs=-1))]).fit(X_tr, df_train['threat_level'])\n",
                    "\n",
                    "dt_p, rf_p, rfc_p = dt.predict(X_te), rf.predict(X_te), rf_c.predict(X_te)\n",
                    "print(f'[4] Árbol de Decisión   -> Acc={accuracy_score(df_test[\"threat_level\"], dt_p)*100:.2f}% | F1(W)={f1_score(df_test[\"threat_level\"], dt_p, average=\"weighted\"):.4f}')\n",
                    "print(f'[5] Random Forest (100) -> Acc={accuracy_score(df_test[\"threat_level\"], rf_p)*100:.2f}% | F1(W)={f1_score(df_test[\"threat_level\"], rf_p, average=\"weighted\"):.4f}')\n",
                    "print(f'    RF Runtime (12)     -> Acc={accuracy_score(df_test[\"threat_level\"], rfc_p)*100:.2f}% | F1(W)={f1_score(df_test[\"threat_level\"], rfc_p, average=\"weighted\"):.4f}')\n",
                    "\n",
                    "# 6. ARIMA (Serie diaria de incursiones HIGH/CRITICAL)\n",
                    "ts = df_clean[['timestamp','high_risk_binary']].copy()\n",
                    "ts['date'] = pd.to_datetime(ts['timestamp']).dt.floor('D')\n",
                    "daily = ts.groupby('date')['high_risk_binary'].sum().sort_index()\n",
                    "daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), freq='D'), fill_value=0).astype(float)\n",
                    "cut = int(len(daily) * 0.80)\n",
                    "arima_fit = ARIMA(daily.iloc[:cut], order=(1,1,1)).fit()\n",
                    "arima_pred = arima_fit.forecast(steps=len(daily) - cut)\n",
                    "y_t = daily.iloc[cut:].to_numpy()\n",
                    "mape = np.mean(np.abs((y_t - arima_pred.to_numpy()) / np.where(y_t==0, 1, y_t))) * 100\n",
                    "print(f'[6] ARIMA(1,1,1)        -> AIC={arima_fit.aic:.2f} | MAE={mean_absolute_error(y_t, arima_pred):.2f} | MAPE={mape:.2f}%')"
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# Matriz de confusion del modelo seleccionado (Random Forest)\n",
                    "labels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']\n",
                    "cm = confusion_matrix(df_test['threat_level'], rf_p, labels=labels)\n",
                    "cm_norm = cm.astype(float) / cm.sum(axis=1)[:, None]\n",
                    "plt.figure(figsize=(7, 5.5))\n",
                    "sns.heatmap(cm_norm, annot=True, fmt='.2%', cmap='Blues', xticklabels=labels, yticklabels=labels)\n",
                    "plt.title(f'Matriz de Confusión Normalizada — Random Forest ({accuracy_score(df_test[\"threat_level\"], rf_p)*100:.2f}%)', fontweight='bold')\n",
                    "plt.xlabel('Predicción'); plt.ylabel('Real')\n",
                    "plt.tight_layout()\n",
                    "plt.show()"
                ]
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "---\n",
                    "## Fase 6: Reglas de Conocimiento, Artefacto Productivo y Orange Data Mining\n",
                    "\n",
                    "- **Decisión productiva:** Se exporta **Random Forest compacto (12 árboles, 95.08% Acc, 862 KB JSON)** junto con Regresión Lineal, Regresión Logística, K-Means (`k=4`) y pronóstico ARIMA(1,1,1) a `backend/app/data/predictive_models_artifact.json`, operado con inferencia pure-NumPy (0 contenedores extra en Oracle).\n",
                    "- **Validación externa e independiente:** Flujo reproducible en `data_mining/orange/AeroGuard_CRISP_DM.ows` sobre lote independiente (`104,400` registros)."
                ]
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "comp_file = os.path.join(dm_dir, 'reports', 'comparativa_6_modelos.json')\n",
                    "if os.path.exists(comp_file):\n",
                    "    with open(comp_file, encoding='utf-8') as fh:\n",
                    "        comp = json.load(fh)\n",
                    "    print('Artefacto JSON:', comp['runtime_artifact_kb'], 'KB | Paridad vs sklearn:', comp['runtime_rf_parity_pct'], '%')\n",
                    "    print(json.dumps(comp['production_decision'], indent=2, ensure_ascii=False))"
                ]
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.14.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }

    nb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CRISP_DM_AeroGuard.ipynb")
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)
    print(f"[OK] Notebook actualizado en: {nb_path}")


if __name__ == "__main__":
    build_notebook()
