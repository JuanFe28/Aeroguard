# Aceptación pendiente del servidor y evidencia para Trello

Fecha: 29/10/2026. Ejecutar desde el portátil con identidad SSH ya autorizada. Comandos: [TXT de casa](../../COMANDOS_SERVIDOR_CASA.txt). No se ejecutó esta lista en el servidor apagado.

El paso 5 del TXT ya llama automáticamente a `run_server_app_qa.py` después del arranque y la comprobación del stack QA. Ejecuta 51 casos de navegador, guarda informe HTML/capturas/inventarios y genera galería visual pendiente de revisión humana. [Cobertura detallada](PRUEBA_COMPLETA_APP.md). No se ejecuta contra producción.

| Paso | Resultado esperado | Evidencia a conservar | Tarjeta / criterio |
|---|---|---|---|
| Identificar revisión | Commit del worktree igual a la entrega descargada; checks de ese HEAD aprobados | SHA, enlace del PR, enlaces de Actions, fecha | DEPLOY-01; nunca usar checks de un commit anterior |
| Arranque del destino | Docker rootless y servicios del stack previo saludables; espacio y memoria suficientes | Salida saneada de diagnóstico y health | DEPLOY-02 básico; comprobar estado actual |
| Respaldar | Dump nuevo, manifiesto SHA-256 y archivos originales de reportes | Nombre/ruta privada del respaldo y manifiesto sin datos personales | OPERATE-01; no subir dump ni reportes privados |
| Validar Compose | Configuración combinada válida, mismo proyecto de producción y puertos solo en loopback | Exit code y lista saneada de servicios/puertos | DEPLOY-02 y MONITOR |
| Prometheus | Servicio disponible; target `aeroguard` en `up`; métricas anónimas bloqueadas | Captura de targets y resultado de autenticación | MONITOR-01 en destino |
| Grafana | Dashboard AeroGuard visible; disponibilidad, solicitudes, latencia y sensores alimentados | Captura de los cuatro paneles, sin claves | MONITOR-02 en destino |
| Alertas | En QA, un sensor sintético sin telemetría produce `AeroGuardSensorStale`; recupera al recibir muestra | Hora de simulación y capturas firing/resolved | MONITOR-03; no detener producción para demostrarlo |
| Receptor externo, si exigido | Notificación recibida en destino autorizado y con fecha verificable | Comprobante saneado, destinatario acordado | MONITOR-03 externo; firing no acredita entrega |
| Construir QA | Test-stage de backend pasa; backend/frontend del commit correcto arrancan con imágenes de QA | Logs, SHA, nombres/digests locales, `check_deploy.py` | TEST-01 / BUILD / nueva candidata |
| PostgreSQL | Mismas regresiones funcionales y de UUID/referencias sobre PostGIS | Resultados de QA del destino; no sustituir por SQLite | TEST-01 y nueva entrega de DEPLOY-02 |
| Recorrido integrado | Telemetría → una detección → trayectoria → alerta asignada/resuelta → reporte original → auditoría coherente | Capturas y resultados con datos sintéticos identificados | TEST-01; aceptación visual pendiente del destino |
| Recuperación real | Backup restaurado en una base nueva y reporte recuperado con el mismo hash | Manifiesto, conteos y descarga del reporte | OPERATE-01; no sobrescribir la BD activa |
| Actualización de producción | Revisión aceptada, imágenes nuevas identificadas, respaldo y plan de retorno disponibles | Acta de aceptación, versión y digests | Nueva candidata; no sobrescribir rc.1 |

## Criterio de parada

Si falla un paso, conservar el resultado y resolverlo antes de continuar con los dependientes. Una falta de capacidad no autoriza detener otros servicios, ampliar permisos ni cambiar las restricciones de red. La compilación y un segundo stack consumen recursos dentro del límite agregado de la cuenta.

## Qué queda preparado sin el servidor

La prueba integrada de la API usa usuarios persistidos y login real, con `APP_ENV=production` y base SQLite aislada. Comprueba permisos, deduplicación de alerta activa, asignación, resolución con nota, CSV que contiene la detección, descarga idéntica, SHA-256 y presencia/verificación de auditoría. No acredita PostGIS ni un vuelo real.

El stack de QA del paso 5 del TXT no incluye Prometheus/Grafana. La prueba de alerta sintética requiere preparar monitoreo separado apuntando al backend de QA, con puertos y secretos propios, o realizarla en otro entorno de pruebas autorizado. El Prometheus del paso 3 observa producción; no mostrará sensores que existen únicamente en la BD de QA. Este montaje y su ejecución quedan pendientes del destino.

El ensayo CI existente de Deploy arranca las imágenes publicadas de rc.1. La validación `handoff-layout` comprueba el Compose nuevo, pero no construye sus imágenes ni demuestra que el monitoreo recolecte datos en el servidor real. Esa diferencia debe conservarse al marcar las tarjetas.

## Retorno a la instalación anterior

El TXT conserva el checkout `/home/aeroguard/AeroGuard`, sus secretos y sus volúmenes, y usa un proyecto distinto para QA. Mientras no se acepte una actualización, esa instalación sigue siendo la referencia. Para detener QA se usa `docker compose ... stop` con **el .env y proyecto de QA**; no `down -v`. Una reversión posterior de producción debe restaurar las imágenes previamente identificadas y comprobar persistencia y compatibilidad; los cambios de este lote no añaden columnas de BD.

## Fuera de un cierre puramente técnico

Sensores físicos, dataset independiente de visión, permisos operacionales, confirmación del RAC consolidado, SMTP/n8n externos y aceptación docente dependen de recursos o decisiones externas. No registrarlos como terminados por disponer de código o documentación.
