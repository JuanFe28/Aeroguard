# Operación académica de AeroGuard 1.2.0

Revisión del 29/10/2026 para la rama `codex/qa-continuation`: incorpora los cambios de QA aún no instalados en el servidor privado. La candidata allí documentada sigue siendo rc.1; el apartado de recuperación del scheduler actualizado describe el código nuevo. La aceptación por entorno está en [la lista del servidor](../qa-2026-10-29/ACEPTACION_SERVIDOR.md).

Este procedimiento corresponde al código corregido el 21-10-2026. La instalación integrada se ensayó en contenedores locales aislados; no equivale a un despliegue aceptado en una VM externa.

## Antes de iniciar

1. Conservar una copia privada de `.env`, del dump de PostgreSQL y de los archivos de reportes. Mantener otra copia fuera del equipo. Git conserva código y documentación, no estos datos.
2. Generar claves propias. Eliminar o cambiar las contraseñas de las antiguas cuentas de demostración si se reutiliza una base. El bootstrap no rota cuentas existentes.
3. Mantener `APP_ENV=production`, `DEBUG=false`, `ALLOW_DEMO_TOKENS=false`, `SEED_DEMO_DATA=false` y `ALLOW_SQLITE_FALLBACK=false`. Compose fija los dos primeros; los otros tres están desactivados por defecto.
4. Registrar sensores con tipo, ubicación, rango y estado correctos. Dar al integrador un JWT de operador dedicado y renovar su sesión antes del vencimiento. Usar el UUID registrado como `sensor_id` y una clave estable por objeto como `object_id`.
5. Mantener un solo proceso backend con esta configuración: el gestor WebSocket reside en memoria. El cierre de sesión revoca todas las sesiones del usuario; un segundo proceso verifica la revocación en su siguiente revisión periódica, hasta 25 segundos sin tráfico.

La clave de Google Maps incrustada en el frontend anterior fue retirada. Su propietario debe revocarla o restringirla en Google Cloud; quitarla del archivo actual no la elimina del historial Git.

## Operador

Entrar con una cuenta individual y comprobar sensores y mapa. Una clasificación visual es experimental: verificar el objeto por un medio independiente y avisar al responsable autorizado. No interpretar un score como precisión ni atribuir fabricante, intención hostil o autorización de contramedidas.

Revisar fecha, sensor y trayectoria antes de asignar una alerta. La asignación desde la interfaz se hace al operador autenticado. Resolver con una nota que describa la verificación realizada. Conservar el registro; no editar la base para ocultar una alerta.

Una API no disponible produce un error visible. La interfaz no debe aceptarse como operativa por mostrar un ejemplo local. Si se pierde la conexión, comprobar `/health` (proceso) y `/ready` (BD y sensores), conservar la hora del incidente y avisar al administrador.

## Analista

Consultar historial y auditoría con los filtros requeridos. Exportar CSV, Excel o PDF y conservar el archivo original y su SHA-256. Una huella detecta cambios; no es firma digital ni certificación pericial. La fuente es la BD, que también puede contener muestras sembradas en desarrollo. Los reportes se limitan a 5.000 filas e indican truncamiento; dividir el rango cuando corresponda.

Las fechas de los filtros de reportes abarcan días completos en UTC. La API recibe instantes ISO 8601. Las programaciones usan cron de cinco campos y UTC; revisar `next_run`, `last_run` y la lista de reportes. En el código corregido del 29/10, reporte y avance del cron se confirman en una transacción; los errores con rollback conservan la fecha vencida para reintentar. No se reconstruyen todos los intervalos históricos perdidos. Una caída puede dejar archivos sin registro y un corte durante el commit tiene resultado incierto: revisar antes de regenerar manualmente. No hay entrega automática por correo ni garantía distribuida de ejecución exactamente una vez. Véanse [las pruebas de recuperación y sus límites](../qa-2026-10-29/SCHEDULER_RECUPERACION.md). La imagen antigua rc.1 aún presenta el riesgo anterior de omitir una ejecución.

## Roles y estados de usuario

| Rol | Operaciones disponibles en la API |
|---|---|
| Administrador | Usuarios, configuración, sensores, zonas, detecciones, alertas, reportes y auditoría |
| Operador | Consulta detecciones/zonas/sensores; ingesta telemetría; gestiona detecciones y alertas; consulta historial |
| Analista | Consulta detecciones, alertas, zonas e historial; genera/descarga reportes y consulta auditoría |

El operador no genera ni descarga reportes; el analista no asigna ni resuelve alertas. La restricción la aplica la API aunque alguien abra una ruta de interfaz manualmente. Desactivar una cuenta o cambiar su rol revoca las sesiones anteriores. Reactivarla requiere un login nuevo. Un administrador no puede desactivar ni cambiar el rol de su propia sesión; debe conservarse al menos un administrador activo.

## Trayectorias y datos recibidos

Seleccionar una detección y cargar la trayectoria. La vista muestra las muestras históricas en 2D, los puntos inicial/final y la tabla con fecha, posición, altitud, velocidad y rumbo. Una única muestra no permite reconstruir un recorrido; la pantalla lo indica. Actualizar el selector consulta hasta 50 detecciones recientes. No hay reproducción temporal ni predicción.

Conservar un `object_id` estable por sensor para acumular un seguimiento. La fecha enviada por el sensor se normaliza a UTC; si no incluye zona horaria se interpreta como UTC. Esto no acredita la sincronización de su reloj. La tabla se presenta en la hora local del navegador. La distancia es horizontal y la velocidad media corresponde al promedio de las muestras, no a una estimación por distancia/tiempo.

Cada adaptador debe documentar unidades y referencia vertical AGL/MSL. No tratar una coincidencia con un polígono configurado como una infracción aeronáutica ni una identificación del piloto. La matriz de entidades y fuentes está en [Trayectorias y autoridades](../qa-2026-10-29/TRAYECTORIAS_Y_AUTORIDADES.md).

## Gestión de errores y alertas

El código de QA rechaza UUID inválidos con 422 y referencias inexistentes con 404 en los recursos comprobados. No alterar IDs para evitar estos errores. Las listas de detecciones, alertas, usuarios y auditoría aceptan `skip` no negativo y `limit` entre 1 y 500. En actualización de sensores y campos obligatorios de zonas, omitir conserva el valor; `null` explícito se rechaza.

Antes de asignar una alerta, verificar que el destinatario exista, esté activo y tenga permiso de gestión de alertas. Resolver requiere una nota con contenido. El reporte y la auditoría conservan lo registrado; un resultado de prueba debe identificarse como sintético. El endpoint de detección manual valida la existencia de sensor/zona y exige que la posición coincida con la geocerca activa indicada antes de generar la alerta asociada.

En la interfaz, Perfil consulta la identidad de la sesión; no cambia la contraseña. Ante un error de correo duplicado, corregir el formulario conservado y reenviar. No interpretar un mensaje de éxito de la interfaz como aceptación del despliegue si no corresponde al commit y entorno previstos.

La verificación de auditoría indica si revisó toda la cadena o solo un prefijo. Su punto de control está en la misma BD: un administrador de esa BD podría modificar ambos. La protección contra ese actor requiere anclaje externo, todavía pendiente.

## Monitoreo

`/metrics` exige un token de métricas aleatorio de 32 caracteres como mínimo, o un JWT con `config:read`. El token dedicado no permite operar la API. Guardarlo en `secrets/metrics.token`, declararlo como `METRICS_BEARER_TOKEN` y rotar ambos valores juntos.

Arrancar `docker-compose.monitoring.yml` junto al Compose principal. Grafana provisiona disponibilidad, sensores sin telemetría, solicitudes por segundo y latencia P95. Prometheus evalúa `AeroGuardSensorStale` y `AeroGuardBackendUnavailable`. Una alerta visible en Prometheus no implica envío de SMS, correo ni vigilancia humana permanente; conectar y probar un receptor externo antes de exigir notificaciones.

Los sensores activos se consideran vencidos tras `SENSOR_STALE_SECONDS` (120 por defecto). El healthcheck actualiza la medida cada 30 segundos; Prometheus recoge cada 5 segundos. Verificar la ingestión, el estado del sensor y la sincronización horaria antes de concluir que el hardware falló.

## Backup y recuperación

En una ventana sin escrituras de prueba:

```powershell
python scripts/database_backup.py --container aeroguard-postgres --output backups/fecha-hora.dump --verify-restore --reports-container aeroguard-backend
```

Se genera un dump `pg_dump -Fc`, su manifiesto SHA-256 y una carpeta `.reports` con los archivos originales. La verificación restaura en una base **nueva**, compara conteos de cinco tablas y conserva esa base para inspección. Nunca sustituye la base activa. El dump puede contener hashes de contraseñas y datos operativos: custodiarlo como información privada.

Para recuperar el servicio, verificar el manifiesto, inspeccionar la base restaurada, apuntar una instalación aislada a esa base y restaurar los archivos al volumen de reportes con permisos del usuario del contenedor. Confirmar login, trayectorias, cadena de auditoría y descarga de un reporte por su ID antes de cambiar el servicio activo. Conservar el respaldo anterior hasta la aceptación del responsable. La comparación de conteos no sustituye esta aceptación funcional.

La prueba incluida restauró usuarios, sensores, detecciones, auditoría y reportes en una base nueva. El manifiesto está en `evidencias/backup-restore.json`; los archivos privados están en `backups/`, fuera de Git.

## Fallos de IA, SMTP y actualización

El worker utiliza un JWT de operador. Si expira o pierde permiso, revisar `ai.processing.dead`, renovar la sesión y reprocesar manualmente tras corregir el error. Los trabajos transitorios de red/servidor se reencolan. No confirmar resultados que el backend no haya guardado.

La recuperación de contraseña responde de forma neutra. Sin SMTP no se entrega correo y no se imprime ningún token. Configurar un servidor autorizado y probar entrega antes de ofrecer recuperación a usuarios externos.

Antes de actualizar: respaldo, controles locales, imagen de test Linux, integración en una base aislada, revisión del diff y aceptación. Conservar commit, digests y respaldos. No hacer `down -v` sobre una instalación con datos que deban preservarse.
