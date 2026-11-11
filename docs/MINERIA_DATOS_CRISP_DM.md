# Módulo Integral de Minería de Datos (Metodología CRISP-DM) — AeroGuard C-UAS

**Sistema de Defensa y Monitoreo del Espacio Aéreo Contra Drones No Autorizados**  
**Candidata / Versión de Análisis:** `1.2.0-rc.1` | **Módulo:** `data_mining/`  
**Dataset Auditado:** 125,000 registros de telemetría multi-sensor (Bucaramanga y Bogotá)

---

## 1. Fase 1: Comprensión del Negocio (Business Understanding)

### 1.1 Contexto y Declaración del Problema Operativo
El despliegue de sistemas contra aeronaves no tripuladas (C-UAS, *Counter-Unmanned Aerial Systems*) en entornos urbanos e infraestructuras críticas (bases aéreas, instalaciones gubernamentales, campus educativos como las UTS) enfrenta desafíos operacionales de alta complejidad:
1. **Sobrecarga y Fatiga del Operador:** Los radares y cámaras generan cientos de trazas por minuto. La evaluación puramente visual de cada vector satura al analista táctico.
2. **Falsos Positivos vs. Amenazas Reales:** Aves u objetos arrastrados por el viento activan alarmas perimetrales indiscriminadamente.
3. **Incertidumbre en Tiempo Real:** Determinar si un dron comercial (quadcopter) realiza un sobrevuelo recreativo o si un dron modificado (`diy_custom` / `fixed_wing`) transporta una carga útil hostil hacia el perímetro de exclusión exige correlacionar de forma instantánea variables cinemáticas, de radiofrecuencia (RF), meteorológicas y de visión artificial.

### 1.2 Objetivo del Proyecto de Minería de Datos
Desarrollar un pipeline predictivo automatizado bajo la metodología estándar de la industria **CRISP-DM (Fases 1 a 6)** que:
- Procese telemetría heterogénea multi-sensor a escala (125,000 registros, 20 dimensiones).
- Supere con resiliencia problemas reales de calidad de datos (duplicados de transmisión, nulos de sensor, valores corruptos y anomalías físicas).
- Clasifique con un **Accuracy y F1-Score superior al 92%** el nivel de amenaza (`threat_level`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- Genere reglas de conocimiento táctico explicables para el Centro de Operaciones de Seguridad (SOC).

---

## 2. Fase 2: Comprensión e Identificación de los Datos (Data Understanding)

### 2.1 Diccionario de Datos Completo (20 Atributos)

| N° | Columna | Tipo de Dato | Rango / Unidades | Descripción Operativa C-UAS |
| :---: | :--- | :---: | :---: | :--- |
| **1** | `record_id` | String | `REC-000001`... | Identificador único unívoco de la trama de telemetría. |
| **2** | `timestamp` | DateTime | 2026-01-01 a 2026-10-31 | Estampa de tiempo UTC del evento detectado. |
| **3** | `drone_id` | String | `UAV-HK-xxx`, `UAV-COL-xxx` | Identificador de matrícula o firma de radio del vector aéreo. |
| **4** | `sensor_id` | Categórico | 5 sensores nominales | Sensor receptor (`CAM-BGA-NORTE-01`, `RAD-BGA-SUR-02`, etc.). |
| **5** | `city_zone` | Categórico | `Bucaramanga`, `Bogota` | Área metropolitana o jurisdicción del espacio aéreo protegido. |
| **6** | `latitude` | Float | ~7.119 (BGA) / ~4.609 (BOG) | Coordenada geográfica de latitud del contacto. |
| **7** | `longitude` | Float | ~-73.122 (BGA) / ~-74.081 (BOG)| Coordenada geográfica de longitud del contacto. |
| **8** | `altitude_m` | Float | 5.0 a 300.0 m | Altura sobre el nivel del terreno (AGL). Cota legal: 120 m. |
| **9** | `speed_ms` | Float | 0.0 a 35.0 m/s | Velocidad horizontal de desplazamiento del objetivo. |
| **10** | `vertical_speed_ms` | Float | -10.0 a 15.0 m/s | Tasa de ascenso o descenso vertical. |
| **11** | `heading_deg` | Float | 0.0° a 360.0° | Rumbo de navegación magnético del dron. |
| **12** | `distance_to_zone_m`| Float | 0.0 a 2000.0 m | Distancia radial euclidiana hacia el centro de la zona de exclusión. |
| **13** | `rf_signal_dbm` | Float | -110.0 a -30.0 dBm | Intensidad de señal del enlace de control C2 (RSSI). |
| **14** | `battery_est_pct` | Float | 5.0% a 100.0% | Estimación de autonomía residual de la aeronave. |
| **15** | `ai_confidence` | Float | 0.40 a 0.99 | Certeza del clasificador de visión artificial YOLOv8. |
| **16** | `drone_class` | Categórico | 5 clases | Clasificación aerodinámica (`quadcopter`, `fixed_wing`, `bird_false_pos`, etc.). |
| **17** | `weather_condition` | Categórico | 4 condiciones | Estado meteorológico local (`Despejado`, `Nublado`, `Lluvia`, `Niebla`). |
| **18** | `wind_speed_kmh` | Float | 2.0 a 45.0 km/h | Velocidad del viento ambiental en la cota de vuelo. |
| **19** | `flight_pattern` | Categórico | 5 patrones | Comportamiento de trayectoria (`Directo`, `Evasivo`, `Patrullaje`, etc.). |
| **20** | `threat_level` | Categórico | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | **Variable Objetivo (Target):** Severidad táctica para la toma de decisiones. |

### 2.2 Justificación de Escala: ¿Por qué 125,000 registros y 20 dimensiones?
1. **Representatividad de Clases Críticas Minoritarias:** En operaciones reales de defensa, los incidentes `CRITICAL` son eventos atípicos pero de impacto catastrófico (~8% a 10% del total). Una muestra reducida (ej. 2,000 filas) contendría menos de 150 ejemplos críticos, impidiendo que el algoritmo generalice correctamente las complejas interacciones multidimensionales. Con 125,000 registros se disponen de **más de 10,000 casos críticos**, garantizando un soporte estadístico robusto.
2. **Redundancia Multi-Sensor y Complementariedad:** Ningún sensor individual es infalible:
   - La cámara óptica falla con lluvia o niebla (`weather_condition`).
   - El analizador de espectro RF no detecta drones autónomos con silencio de radio.
   - El radar confunde aves con micro-drones en rangos cortos.  
   Disponer de 20 variables fusionadas permite que los modelos de ensamble capturen patrones latentes de forma no lineal.

### 2.3 Estructura de Ruido Inyectada (80% / 10% / 10%)
El script `data_mining/01_generate_dataset.py` generó el archivo bruto aplicando de forma estricta:
- **80% Limpio Nominal (100,000 registros):** Correlaciones físicas coherentes.
- **10% Outliers Extremos (12,500 registros):**
  - Altitudes imposibles (3,500 m a 9,000 m o negativas aberrantes -200 m).
  - Velocidades supersónicas absurdas para UAVs comerciales (300 a 650 m/s).
  - Distancias de radar fuera de rango (> 150 km).
  - Vientos huracanados categoría 5 (> 250 km/h).
- **10% Datos Sucios (12,500 registros):**
  - **3.5% (4,375 filas):** Nulos (`NaN`) en variables críticas (`altitude_m`, `rf_signal_dbm`, `ai_confidence`).
  - **3.5% (4,375 filas):** Valores corruptos fuera de escala lógica (`ai_confidence = 2.45`, `battery_est_pct = 320%`, strings `"SENSOR_ERR"`, `"???"`).
  - **3.0% (3,750 filas):** Duplicados exactos clonados por fallas en retransmisiones de red.

---

## 3. Fase 3: Preparación y Preprocesamiento de los Datos (Data Preparation)

El pipeline automatizado `data_mining/02_crisp_dm_pipeline.py` ejecutó las siguientes transformaciones de depuración:

1. **Deduplicación:** Se identificaron y eliminaron exactamente **3,750 filas duplicadas (3.00%)**, reduciendo el conjunto inicial de 125,000 a 121,250 registros únicos.
2. **Normalización de Tipos y Tokens Corruptos:** Los strings `"SENSOR_ERR"`, `"???"` y `"CORRUPTED_HEX_0xFF"` fueron convertidos a `np.nan`, y las columnas se coercieron estrictamente a tipos numéricos continuos.
3. **Control de Rango Físico:** Valores aberrantes de confianza IA (< 0 o > 1) y batería (< 0% o > 100%) fueron saneados.
4. **Filtrado Racional de Outliers:** Se removieron las aberraciones físicas inyectadas (altitudes > 1,500m, velocidades > 100 m/s, distancias radar > 25 km), obteniendo un **dataset limpio final de 108,750 registros**, superando ampliamente el umbral exigido de $\ge 105,000$ filas.
5. **Imputación Estadística de Nulos:**
   - Variables numéricas: Imputación por **mediana** (robusta ante colas de distribución).
   - Variables categóricas: Imputación por **moda**.
6. **Codificación y Escalado:**
   - Las variables categóricas (`drone_class`, `flight_pattern`, `weather_condition`, `city_zone`) fueron codificadas mediante `LabelEncoder`.
   - Las características numéricas continuas fueron estandarizadas con `StandardScaler` ($\mu = 0, \sigma = 1$).
7. **Persistencia:** El dataset depurado se almacenó en `data_mining/data/aeroguard_clean_telemetry.csv` (18.88 MB).

---

## 4. Fases 4 y 5: Modelado y Evaluación Comparativa (Modeling & Evaluation)

### 4.1 Estrategia de Partición
- Muestreo estratificado 80/20 (`stratify=y`) para conservar la proporción exacta de las 4 clases de amenaza:
  - **Conjunto de Entrenamiento:** 87,000 registros.
  - **Conjunto de Prueba:** 21,750 registros.

### 4.2 Tabla Comparativa de Modelos Supervisados

| Métrica | Random Forest Classifier (100 árboles, depth=16) | Decision Tree Classifier (depth=12) | Umbral Requerido | Cumplimiento |
| :--- | :---: | :---: | :---: | :---: |
| **Accuracy Global** | **94.09%** | **94.23%** | $> 92.00\%$ | **APROBADO** |
| **Precision (Weighted)** | **0.9420** | **0.9427** | $> 0.9200$ | **APROBADO** |
| **Recall (Weighted)** | **0.9409** | **0.9423** | $> 0.9200$ | **APROBADO** |
| **F1-Score (Weighted)** | **0.9408** | **0.9422** | $> 0.9200$ | **APROBADO** |
| **F1-Score (Macro)** | **0.9349** | **0.9376** | $> 0.9000$ | **APROBADO** |

### 4.3 Reporte Detallado de Clasificación por Categoría (Mejor Modelo)

```text
              precision    recall  f1-score   support

         LOW       0.97      0.96      0.96      4465
      MEDIUM       0.92      0.96      0.94      8079
        HIGH       0.95      0.92      0.94      7424
    CRITICAL       0.92      0.89      0.91      1782

    accuracy                           0.94     21750
   macro avg       0.94      0.93      0.94     21750
weighted avg       0.94      0.94      0.94     21750
```

- La clase `LOW` alcanza un **F1 de 0.96** gracias a la separación unívoca de falsos positivos (aves) y vuelos distantes.
- Las clases `MEDIUM` y `HIGH` mantienen un balance superior a **0.94**.
- La clase `CRITICAL` alcanza una **precisión de 0.92**, minimizando falsas alarmas de máxima alerta.

---

## 5. Gráficas Generadas de Evidencia (`data_mining/reports/figures/`)

El pipeline generó 6 visualizaciones en alta resolución (300 DPI):

1. **`01_boxplot_outliers_antes.png`:** Muestra con claridad los outliers inyectados en altitud (> 3,500 m), velocidad supersónica (> 300 m/s) y distancias de radar distorsionadas (> 150 km).
2. **`02_mapa_nulos_y_calidad.png`:** Gráfico de barras horizontal que evidencia las variables afectadas por nulos (3.5%), datos corruptos (3.5%) y las filas duplicadas (3.0%).
3. **`03_boxplot_limpio_despues.png`:** Evidencia la recuperación del espacio físico de vuelo tras la limpieza (altitudes acotadas a cotas C-UAS, velocidades normales hasta 35 m/s).
4. **`04_matriz_correlacion.png`:** Mapa de calor de correlaciones lineales de Pearson, destacando la fuerte correlación inversa de `distance_to_zone_m` con el nivel de amenaza y la correlación directa de `speed_ms` y `altitude_m`.
5. **`05_matriz_confusion.png`:** Matriz de confusión normalizada del mejor modelo sobre las 21,750 muestras de prueba, confirmando diagonales dominantes entre el 89% y el 96%.
6. **`06_importancia_variables_feature_importance.png`:** Ranking de ganancia de información (Gini). Demuestra que `distance_to_zone_m`, `speed_ms`, `flight_pattern` y `altitude_m` explican más del 65% de la decisión del clasificador.

---

## 6. Fase 6: Despliegue y Conocimiento Táctico Descubierto (Deployment & Knowledge)

### 6.1 Reglas de Conocimiento Operativo (Business Insights)
Las cuatro reglas se **calculan** en `02_crisp_dm_pipeline.py` sobre el dataset limpio (108,750 registros) y se guardan en `data_mining/reports/reglas_conocimiento.json`. Valores obtenidos con la semilla 42:

> **Advertencia metodológica.** El dataset es **sintético**: `threat_level` lo asigna `01_generate_dataset.py` con un puntaje por reglas (distancia, velocidad, patrón, tipo de dron, RF, etc.). Por eso las reglas y el accuracy del 94% muestran que el modelo **recupera las reglas del generador**; no demuestran el comportamiento de drones reales. Validar con datos reales antes de usarlas operativamente.

1. **Proximidad y vector cinético:** si `distance_to_zone_m` < 150 m, `speed_ms` > 20 m/s y `flight_pattern` es `Directo` o `Evasivo`, el **87.8%** de los 1,237 eventos es `CRITICAL` (frente al 8.2% de base general).
2. **Techo de 120 m AGL y drones no comerciales:** con altitud > 120 m y tipo `diy_custom` o `fixed_wing`, la proporción `HIGH`/`CRITICAL` es **69.9%** frente a 35.8% en el resto (**+34.1 puntos porcentuales**, n = 20,747).
3. **Descarte de falsos positivos (aves):** el **100%** de los 8,761 registros `bird_false_pos` es `LOW`, porque el generador así lo define.
4. **Potencia RF:** con señal > -50 dBm la proporción `HIGH`/`CRITICAL` es **53.2%** frente a 39.4% con señal ≤ -50 dBm (n = 23,217). Es una asociación en el dataset sintético; no prueba la ubicación del piloto.

### 6.2 Artefactos de Despliegue Generados
- **Modelo Serializado:** `data_mining/models/aeroguard_threat_model.pkl` (0.20 MB). Contiene el clasificador entrenado, el escalador `StandardScaler`, los diccionarios de codificación categórica y los metadatos de versión.
- **Notebook Interactivo para Sustentación:** `data_mining/CRISP_DM_AeroGuard.ipynb`. Contiene las celdas explicativas y ejecutables de las 6 fases de CRISP-DM listas para ser corridas en JupyterLab, VS Code o Google Colab.
- **Scripts Automatizados:**
  - `data_mining/01_generate_dataset.py` (Generación de los 125,000 registros en segundos).
  - `data_mining/02_crisp_dm_pipeline.py` (Ejecución integral del pipeline y generación de reportes).

---

## 7. Instrucciones de Reproducción Local

Para ejecutar y reproducir el pipeline completo desde la terminal:

```powershell
# 1. Generar el dataset sintetico de 125,000 filas con inyeccion de ruido
.venv/Scripts/python.exe data_mining/01_generate_dataset.py

# 2. Ejecutar el pipeline CRISP-DM completo (Limpieza, graficas, modelos y exportacion)
.venv/Scripts/python.exe data_mining/02_crisp_dm_pipeline.py

# 3. Abrir el notebook para sustentacion interactiva
.venv/Scripts/python.exe -m jupyter notebook data_mining/CRISP_DM_AeroGuard.ipynb
```

