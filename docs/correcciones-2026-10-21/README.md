# Correcciones verificadas — 21 de octubre de 2026

Revisión posterior a la auditoría inicial, sobre la rama `fix/release-readiness`. Versión de trabajo 1.2.0; no es una release publicada.

Se corrigieron dependencias, revocación de sesiones, recuperación de contraseña, límites de intentos, configuración persistida, reportes de BD, recuperación de archivos por ID, programación UTC, seguimiento de telemetría, consultas PostGIS, persistencia del worker RabbitMQ, rutas del frontend y escape de HTML. Se incorporaron Prometheus, alertas y Grafana con configuración reproducible.

## Evidencia disponible

| Comprobación | Resultado y evidencia |
|---|---|
| Python/JS, pruebas, cobertura, carga y seguridad | `evidencias/final/summary.json`: controles aprobados; 94 pruebas funcionales y 3 de carga. Cobertura aproximada 70,97 % sobre el backend ampliado. |
| Dependencias | `evidencias/final/dependencies.json`: cero vulnerabilidades conocidas en el entorno consultado. No garantiza ausencia de vulnerabilidades futuras. |
| Análisis estático | Cero hallazgos medios/altos; 40 bajos conservados en `evidencias/final/bandit.json`, incluidos asserts de verificación y llamadas a subprocess sin shell. No se interpreta como ausencia total de riesgo. |
| WebSockets | `evidencias/final/load/resultados.json`: 10, 50 y 100 clientes, sin pérdida ni errores; P95 de 100 clientes 36,682 ms en esta ejecución local. |
| PostgreSQL/PostGIS/RabbitMQ | `evidencias/deployment.json`: arranque de producción, geocerca, continuidad de trayectoria, deduplicación de alertas, reporte recuperable, auditoría concurrente y resultado del worker persistido. |
| Recuperación PostgreSQL | `evidencias/backup-restore.json`: restauración en base nueva y comparación de cinco tablas. Dumps y reportes privados fuera de Git. |
| Observabilidad | `evidencias/monitoring.json`: target Prometheus activo, alerta real de sensor vencido y dashboard Grafana de cuatro paneles provisionado. |
| Navegador | `evidencias/browser/`: login real, mapa con tiles, sensores y reportes servidos por Docker. El ensayo ampliado se registra por separado en el cierre. |

Las primeras ejecuciones se conservan como historial: `checks-01` detectó dos observaciones medias en el script de backup, corregidas antes del control final. Las evidencias históricas no deben confundirse con la última ejecución del código.

## Trazabilidad de Trello

El tablero no se modificó. La fuente sigue siendo el JSON exportado por el usuario, no una lectura actual de Trello.

- **RELEASE-01:** política SemVer y changelog preparados; no implica tag estable ni aceptación académica.
- **OPERATE-01:** procedimiento y restauración PostgreSQL ensayados en base nueva.
- **OPERATE-02:** manual para operador y analista disponible en [OPERACION.md](OPERACION.md).
- **MONITOR-01, MONITOR-02 y MONITOR-03:** métricas, recolección, dashboard y alerta por sensor vencido comprobados en contenedores locales. La notificación a un receptor externo no está configurada.
- **CODE-02 y CODE-06:** reportes físicos de BD y consultas PostGIS cuentan con evidencia de integración nueva.
- **BUILD-01, TEST-01, TEST-02 y TEST-03:** verificaciones locales y de contenedor documentadas; revisar el manifiesto de cierre para la última revisión exacta.
- **DEPLOY-01:** workflow preparado; su aceptación exige comprobar Actions en GitHub.
- **RELEASE-02 y DEPLOY-02:** la publicación de imágenes y el despliegue en VM externa requieren ejecución y aceptación separadas.

CODE-01 acredita integración experimental; no valida reconocimiento de drones reales. CODE-05 no acredita un workflow n8n desplegado. No marcar una fase comercial completa por estos resultados locales.

Consulta [OPERACION.md](OPERACION.md) y [VERSIONADO.md](VERSIONADO.md) para instalación, respaldos y publicación.
