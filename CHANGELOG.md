# Changelog

## [Unreleased] — QA del 29-10-2026

- Corregidos configuración, edición de sensores/usuarios, Perfil y mapas; trayectorias históricas con tabla y estados explícitos.
- Eliminados incidentes iniciales y telemetría de respaldo ficticios de SOAR.
- Reportes programados y avance del cron confirmados juntos para permitir recuperación tras errores.
- Añadidas validaciones de UUID, referencias, límites numéricos/paginación y notas de resolución; detección manual y alerta asociada persistidas juntas tras validar la geocerca.
- Ampliadas las regresiones de roles, sesiones y recorrido integrado de telemetría a auditoría; preparados comandos de servidor y Compose privados de Monitor/QA.
- Cambios aún sin release nueva ni actualización del servidor. Ver `docs/qa-2026-10-29/SIGUIENTE_CANDIDATA.md` para aceptación y límites.

Este registro describe el código y la preparación local. No prueba que haya versiones publicadas. La política SemVer propuesta está en `docs/auditoria-2026-10-21/02_RELEASE.md`.

## [1.2.0-rc.1] — 2026-10-26

### Release académica

- Definida la política SemVer y alineada la identificación de la candidata en la API, la plantilla de configuración y los metadatos Python.
- Automatizada la validación, construcción y publicación de backend, frontend, ai-service y simulator en GHCR mediante GitHub Actions.
- Conservadas las pruebas en Linux, la auditoría de dependencias, los digests de las imágenes y los artefactos de cada ejecución.
- La candidata reúne las correcciones del 21 de octubre descritas a continuación. Sigue siendo un prototipo académico y no una versión operativa validada.

## Historial de preparación de la candidata

### Candidata de trabajo 1.2.0 — 21-10-2026

- Actualizadas las dependencias vulnerables y reemplazados python-jose/Passlib por PyJWT/bcrypt directo. El entorno auditado ya no presenta vulnerabilidades conocidas; restricciones reproducibles en `constraints.txt`.
- Revocación persistente de sesiones y WebSockets, recuperación de contraseña de un solo uso y límites atómicos de intentos. Sin tokens en logs ni credenciales de demostración sembradas por SQL en producción.
- Reportes consultados en BD, archivos originales recuperables por ID, verificación de integridad, exportación CSV real, protección de celdas y programación UTC persistente.
- Telemetría enlazada con sensores y objetos, trayectoria acumulada y alertas activas sin duplicados. Configuración validada, persistida y aplicada en las operaciones.
- PostGIS con geometría mantenida por trigger, índice GiST y selección espacial mediante ST_Covers. Worker RabbitMQ idempotente, con reintento de red y cola de errores.
- Corregidos login real, rutas y formatos esperados por el frontend; errores visibles, escape de texto/atributos y ausencia de resultados ficticios de respaldo en modo real.
- Producción sin fallback silencioso a SQLite. Métricas autenticadas, Prometheus y Grafana provisionados, disponibilidad y alerta por sensor vencido.
- Construidas las cuatro imágenes y ejecutadas pruebas en Linux, integración PostgreSQL/PostGIS/RabbitMQ, navegador y restauración en una base nueva. Manifiestos y evidencias en `docs/correcciones-2026-10-21`.

Las notas que siguen corresponden a la preparación anterior. Sus pendientes de dependencias, construcción y recuperación fueron resueltos por esta candidata; aceptación académica, CI remoto, publicación de imágenes y VM externa siguen pendientes. Todavía no existe una release oficial 1.2.0.

### Corregido

- Se exigen autenticación y permisos en telemetría y dictámenes operativos.
- La verificación de auditoría utiliza el mismo génesis que la escritura.
- Se rechazan imágenes corruptas y cargas superiores a 10 MiB; se limitan dimensiones.
- Visión identifica el motor utilizado y declara que no está validado; YOLO solo acepta clases explícitas de dron.
- La telemetría sin análisis de imagen no atribuye resultados de IA ni confianza constante.
- Demo y reportes indican datos sintéticos; las reglas locales no recomiendan interferencia ni atribuyen intención hostil.
- APP_VERSION predeterminado se alinea con la identificación interna existente 1.1.0.
- Empaquetado del backend preparado con requisitos de test/detector, un worker y ruta persistente de reportes coherente. Construcción Docker pendiente de verificar.

### Añadido

- Quince casos nuevos de regresión y validación de entradas; verificador de Release con evidencias por ejecución.
- CI y construcción manual de imágenes sin publicación; todavía no ejecutados en GitHub.
- Auditoría, matriz de Release, investigación comercial con fuentes, inventario documental, roadmap, guía y notas de candidata.
- Opciones de Selenium sin ventana y carpeta de evidencias configurable.

### Pendiente

- Triaje de vulnerabilidades de dependencias, build/smoke con Docker, PostgreSQL, restauración, aceptación académica y publicación autorizada de imágenes.
- Validación real de detección y cierre de brechas de integración/operación antes de piloto o comercialización.

## [1.1.0 — identificación interna, sin tag publicado]

- `076b0b6` — 15-10-2026: base registrada de planificación, implementación y empaquetado. Las afirmaciones históricas de IA/PostGIS deben contrastarse con la auditoría.
- `28c955f` — 19-10-2026: demo local, ampliación de pruebas de API y correcciones de seguridad. Evidencia histórica: 64 pruebas funcionales y 3 de carga, cobertura 70,21 % y Bandit 0 medios/altos con 17 bajos.

No se identificaron etiquetas remotas en la consulta del 21-10-2026. Las notas de una candidata futura deberán referenciar el commit y los digests realmente aprobados.
