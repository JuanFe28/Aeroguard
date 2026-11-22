# Análisis de las tres gráficas — AeroGuard

**Alcance:** 153 casos artificiales evaluados con reglas conocidas. No es una prueba de detección de drones reales.

1. **Efectividad:** el reactivo simple acertó 71.9 % y el basado en objetivos 100.0 % frente a las reglas de referencia definidas para este experimento. La mejora representa manejo de confianza baja y datos inválidos, no capacidad de reconocimiento visual.
2. **Eficiencia:** se midió la mediana de 10 ejecuciones secuenciales para 10, 50, 100 y 500 decisiones. El modelo basado en objetivos puede consumir más tiempo por las verificaciones y trazabilidad, pero estos tiempos excluyen API, red, persistencia y sensores. Resultados exactos en `metricas.json`.
3. **Distribución:** el reactivo solo monitorea/notifica; el basado en objetivos permite solicitar datos y revisión de baja confianza, evitando tratar todos los casos como evidencia concluyente.

**Limitaciones:** referencias definidas con las mismas reglas de negocio; no evalúan generalización, falsos positivos frente a etiquetas independientes ni sistemas físicos.
