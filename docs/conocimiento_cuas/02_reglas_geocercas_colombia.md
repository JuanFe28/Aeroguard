# Reglas de Geocercas y Zonas Restringidas (Bucaramanga y Bogotá)

## 1. Zonas Críticas Registradas en AeroGuard
- **Aeropuerto Palonegro (Bucaramanga - Área Crítica):** Prioridad `CRITICAL`. Techo operativo configurado de referencia para corredores de aproximación y pista principal. Cualquier incursión activa por debajo o dentro del polígono exige verificación prioritaria.
- **Complejo Gubernamental Santander (Bucaramanga):** Prioridad `HIGH`. Techo configurado en `300 m`. Protege infraestructura institucional y sedes administrativas.
- **Aeropuerto El Dorado (Bogotá):** Prioridad `CRITICAL`. Corredores aeroportuarios principales de máxima sensibilidad aeronáutica.
- **Centro de Operaciones Bogotá:** Prioridad `HIGH`. Techo `500 m`. Zona institucional de control.
- **Zona Residencial Norte Bogotá:** Prioridad `MEDIUM`. Techo `200 m` sobre zonas urbanas densas y sedes diplomáticas.

## 2. Evaluación Geoespacial (PostGIS + Validación)
- En producción sobre PostgreSQL/PostGIS se emplean índices espaciales **GiST** y `ST_Covers` sobre polígonos cerrados validados.
- La detección manual y la ingesta de telemetría validan altitudes coherentes (`min_altitude <= max_altitude`) y persisten punto geográfico, detección y alerta dentro de una transacción unificada.
- Superar una referencia de **120 m** sin contexto de polígono no demuestra por sí solo invasión geográfica de geocerca.
