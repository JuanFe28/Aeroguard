# Operación académica de AeroGuard 1.2.0

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

Las fechas de la interfaz abarcan días completos en UTC. La API recibe instantes ISO 8601. Las programaciones usan cron de cinco campos y UTC; revisar `next_run`, `last_run` y la lista de reportes. La adquisición evita ejecución duplicada; una caída tras adquirir el trabajo puede omitir una ejecución, que debe regenerarse manualmente. No hay entrega automática por correo ni garantía de ejecución exactamente una vez.

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
