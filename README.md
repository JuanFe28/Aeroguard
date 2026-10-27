# AeroGuard

Prototipo académico de monitoreo de objetos aéreos: FastAPI, PostgreSQL/PostGIS, WebSockets, RabbitMQ y una interfaz JavaScript. Candidata académica **1.2.0-rc.1**, identificada y publicada mediante el flujo de Release en GitHub Actions y GHCR. La política de versiones está en [VERSIONING.md](VERSIONING.md).

La API y el frontend usan datos persistidos por defecto. La exposición local puede sembrar ejemplos de forma explícita. La visión usa heurísticas OpenCV/Pillow o un adaptador YOLO opcional: **no existe un modelo de drones validado con un conjunto de prueba independiente**. No se han probado sensores físicos, identificación de fabricante ni funciones de neutralización.

## Estado comprobado

- Autenticación JWT con revocación persistente, recuperación de un solo uso, límites de intentos y permisos por rol.
- Telemetría asociada a sensores, seguimiento por `object_id`, trayectorias y alertas de geocerca sin duplicados activos.
- Consultas espaciales con PostGIS e índice GiST en PostgreSQL; geometría en memoria para la exposición SQLite.
- PDF, Excel y CSV consultan la BD y respetan filtros. Los reportes guardados conservan el archivo original y verifican su hash al descargar.
- Programaciones de reportes persistidas en UTC, con adquisición atómica del trabajo vencido.
- Worker RabbitMQ con persistencia idempotente y cola de mensajes rechazados; análisis experimental identificado expresamente.
- Métricas autenticadas, Prometheus, alertas de sensores y dashboard provisionado en Grafana.
- Cuatro imágenes construidas; pruebas de Linux, navegador, PostgreSQL/PostGIS, RabbitMQ y restauración verificadas.

Las evidencias y el estado de Trello están en [correcciones del 21-10-2026](docs/correcciones-2026-10-21/README.md). Los [informes iniciales de auditoría](docs/auditoria-2026-10-21/README.md) son históricos: sus pendientes pueden haber quedado resueltos en esta revisión.

## Preparación de Deploy privado

La candidata publicada puede ensayarse con [el paquete de despliegue privado](deploy/README.md). Utiliza imágenes fijadas por digest, credenciales generadas localmente, redes separadas y un único puerto en `127.0.0.1`, accesible mediante túnel SSH. La preparación no instala nada en un servidor remoto. **DEPLOY-02 permanece pendiente de la comprobación en el servidor real.**

## Exposición local en Windows

Requiere Python 3.11 y Node para los controles de sintaxis.

```powershell
py -3.11 -m venv .venv
.venv/Scripts/python.exe -m pip install -c constraints.txt -r backend/requirements-expo.txt
.venv/Scripts/python.exe scripts/expo_local.py
```

Abre [la interfaz local](http://127.0.0.1:3000) y entra con `admin` / `Admin@12345` en una base nueva. El script activa datos de ejemplo y SQLite solamente para desarrollo. Las cuentas ya existentes conservan sus contraseñas. El frontend se autentica contra la API; no cambia automáticamente a resultados ficticios si la API falla.

No abras el HTML con `file://`: los módulos y peticiones necesitan un servidor HTTP. El modo de demostración del frontend exige cambiar explícitamente `AEROGUARD_DEMO_MODE` a `true` y no debe utilizarse como evidencia de integración real.

## Docker

```powershell
Copy-Item .env.example .env
# Editar .env: generar SECRET_KEY, POSTGRES_PASSWORD, RABBITMQ_DEFAULT_PASS
# y BOOTSTRAP_ADMIN_PASSWORD propios. No reutilizar los valores de ejemplo.
docker compose up -d --build
```

La interfaz queda en [localhost](http://localhost) y la API en [localhost:8000/docs](http://localhost:8000/docs). La configuración del frontend usa el proxy del mismo origen. PostgreSQL, RabbitMQ y el puerto directo del backend se limitan a la interfaz local del host.

Compose ejecuta el backend en producción: rechaza la clave JWT de ejemplo, DEBUG, tokens/datos de demostración y fallback SQLite. `BOOTSTRAP_ADMIN_PASSWORD` crea un administrador cuando no existe; no modifica cuentas existentes. Una base reutilizada requiere revisar y cambiar las contraseñas antiguas. Las tablas nuevas y la geometría PostGIS se añaden durante el arranque; respalda primero una instalación existente.

El simulador y el worker son perfiles opcionales. Registra los sensores antes de enviar telemetría en producción. El simulador necesita `SIMULATOR_TOKEN`; el worker necesita `AI_WORKER_TOKEN` de un usuario operador dedicado. Estos JWT deben renovarse al expirar.

```powershell
docker compose --profile ai up -d ai-service
docker compose --profile demo up -d simulator
```

La cola `ai.processing` acepta JSON con `detection_id` e `image_base64`. Los resultados se consultan en `/api/v1/detections/{id}/ai-analysis`; los errores permanentes quedan en `ai.processing.dead`. Un mensaje no acredita precisión de reconocimiento.

## Observabilidad y operación

Consulta [el manual de operación y recuperación](docs/correcciones-2026-10-21/OPERACION.md). Configura un `METRICS_BEARER_TOKEN` aleatorio de al menos 32 caracteres y guarda el mismo valor en `secrets/metrics.token`; configura también `GRAFANA_ADMIN_PASSWORD`.

```powershell
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml --profile monitoring up -d
```

Prometheus queda en [localhost:19090](http://localhost:19090) y Grafana en [localhost:13000](http://localhost:13000). El token de métricas permite únicamente `/metrics`. El monitor de sensores usa el último paquete recibido; no diagnostica por sí solo fallos físicos. SMTP y un receptor externo de alertas requieren configuración del operador.

## Verificación y respaldo

```powershell
.venv/Scripts/python.exe scripts/release_checks.py --output tmp/mi-verificacion --audit-dependencies
docker build --target test -f backend/Dockerfile .
.venv/Scripts/python.exe scripts/database_backup.py --output backups/respaldo.dump --verify-restore --reports-container aeroguard-backend
```

Usa carpetas y nombres nuevos para conservar las ejecuciones anteriores. Los respaldos, bases, reportes generados, sesiones y `.env` quedan fuera de Git. El respaldo PostgreSQL contiene información privada: no debe subirse como código fuente.

La publicación de imágenes, ejecución de Actions en GitHub, despliegue en una VM y aceptación docente siguen siendo pasos separados. Consulta [el changelog](CHANGELOG.md) y la [política de versionado](docs/correcciones-2026-10-21/VERSIONADO.md).
