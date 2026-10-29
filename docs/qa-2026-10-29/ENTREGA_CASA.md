# Entrega para retomar en casa

**Publicación bloqueada:** la integración de GitHub respondió 403 al crear la rama. La consulta de cuentas guardadas fue rechazada por la revisión automática; no se accedió a las credenciales. Se preparó `ENTREGA_CASA_20261029.zip` para traslado manual, con instrucciones en `LEEME_PUBLICAR_CASA.txt`. Ni el TXT ni las correcciones están confirmados en GitHub. Los checks nuevos de CI todavía no se ejecutaron.

Los comandos están en [COMANDOS_SERVIDOR_CASA.txt](../../COMANDOS_SERVIDOR_CASA.txt), en la rama `codex/qa-continuation`. El servidor estaba apagado; no se ejecutaron esos bloques.

## Cerrado localmente en este lote

- Trece pruebas nuevas de aceptación de roles con usuarios persistidos y login real: matriz de lecturas, desactivación/reactivación, revocación tras cambio de rol y protección de la propia cuenta administradora. Se ejecuta la autenticación en modo producción sobre SQLite de prueba, no con usuarios inventados por tokens demo.
- Dos pruebas nuevas de preparación de Monitor: conserva el `.env` de aplicación y los secretos de Grafana, y rechaza un token existente distinto sin sobrescribirlo.
- Compose de monitoreo compatible con las redes de `deploy/compose.yml`; el anterior Compose de monitoreo era para el stack de desarrollo.
- Compose independiente para compilar el código nuevo en una instalación de QA con nombre, puerto y volúmenes diferentes de producción.
- Comandos de PowerShell con eliminación de retornos CR al enviarlos a bash, diagnóstico sin secretos, descarga en worktree separado, respaldo y verificaciones del target Prometheus y salud Grafana.

Resultado local: **141 pruebas aprobadas, 7 omitidas por falta de Docker Compose y 7 subpruebas aprobadas; 10 pruebas frontend aprobadas**. Bandit del preparador sin hallazgos medios/altos. El workflow de PR incorpora validación del Compose combinado en un runner con Docker; consultar su resultado remoto antes de ejecutar la entrega.

## Pendiente de ejecutar o aceptar

1. Checks remotos de esta entrega y validación de Compose en Linux.
2. Encender el servidor, verificar arranque y margen de recursos desde el portátil autorizado.
3. Ejecutar los bloques del TXT por etapas. No mezclar `.env` de producción y QA.
4. Verificar dashboard y alertas en el destino. Una comprobación HTTP no sustituye la prueba controlada de una alerta ni la entrega a un receptor externo.
5. Construir/probar el código nuevo en QA con PostgreSQL. Aceptar los recorridos de la aplicación y una recuperación real antes de preparar la actualización de producción.

El objetivo es dejar la ejecución sobre el servidor como el siguiente trabajo práctico. **No se declara terminado todo el producto**: sensores físicos, validación independiente de visión, referencia de altitud, SMTP/n8n, revisión normativa consolidada y aceptación docente conservan sus condiciones externas. La siguiente versión publicada y la integración del PR también requieren revisión; no se sobrescribió la candidata rc.1.

Trello: usar [ESTADO_TRELLO.md](ESTADO_TRELLO.md). Los archivos y pruebas locales no cierran por sí solos MONITOR en el destino ni actualizan el tablero.
