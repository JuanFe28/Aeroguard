# Conocimiento Táctico Extraído de Minería de Datos (CRISP-DM)

## 1. Modelos Predictivos Desplegados en AeroGuard
- **Clasificador Principal (`Random Forest` compacto 12 árboles):** Exactitud **95.08 %** en prueba ciega (20 %) y **95.19 %** en Lote 2 independiente (`104,400` registros limpios), inferido en memoria con NumPy sin `scikit-learn` en el contenedor productivo (`862.4 KB`).
- **Puntaje Continuo de Riesgo (`Regresión Lineal`):** Predice `risk_score` (0 a 100) con $R^2 = 0.9356$ y MAE $= 4.24$.
- **Probabilidad de Violación / Alto Riesgo (`Regresión Logística`):** ROC-AUC $= 0.9689$ con umbral de decisión calibrado en **0.40** (`F1 = 0.8821`).
- **Perfiles Cinemáticos (`K-Means`, $k=4$):** Identifica 4 perfiles operativos (`Aproximación Cercana al Perímetro` con 57.81 % de eventos `HIGH`/`CRITICAL`, `Sobrevuelo Elevado > 120 m` con 61.52 %, `Tránsito Rápido Perimetral` con 43.57 % y `Vuelo Distante / Baja Energía` con 6.78 %).
- **Pronóstico Temporal (`ARIMA(1,1,1)`):** Estima picos diarios a 14 días con `MAPE = 6.77 %` sobre la serie histórica.

## 2. Reglas de Conocimiento Descubiertas (Sobre Dataset Sintético)
1. **Proximidad y velocidad:** Con `distance_to_zone_m < 150 m`, `speed_ms > 20 m/s` y patrón `Directo` o `Evasivo`, el **87.8 %** de los contactos corresponde a `CRITICAL`.
2. **Aves (`bird_false_pos`):** El **100.0 %** de los falsos positivos aviares pertenece a `LOW`; útil para reducir fatiga de alarma verificando primero si existe evidencia visual de ave.
3. **Techo 120 m + aeronaves artesanales o ala fija (`diy_custom`, `fixed_wing`):** Incrementa la tasa `HIGH`/`CRITICAL` al **69.9 %** (`+34.1 pp` frente al resto).
4. **Rigor académico:** Estos parámetros describen el generador sintético CRISP-DM y apoyan al analista; no reemplazan sensores calibrados ni validación en campo.
