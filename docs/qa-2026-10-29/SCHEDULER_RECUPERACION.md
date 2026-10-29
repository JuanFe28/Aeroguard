# Recuperación de reportes programados

Revisión local: 29 de octubre de 2026, rama `codex/qa-continuation`.

## Problema y cambio

El scheduler confirmaba `next_run` y `last_run` al adquirir una programación vencida, antes de crear su reporte. Si la generación fallaba o el proceso se interrumpía después de esa confirmación, la ejecución quedaba omitida hasta la siguiente fecha cron.

Ahora la actualización condicional de la programación conserva su transacción abierta. `persist_report` confirma juntos el registro del reporte y el avance de la programación. Un error con rollback o la cancelación antes de persistir deja la fecha vencida para un nuevo intento. La condición exige además que la programación continúe activa. Dos ejecuciones que toman la misma fecha compiten por esa actualización; solo una puede confirmarla.

Se guardan valores independientes de los objetos ORM para recorrer el lote: un rollback no expira los datos de las programaciones restantes. El propietario se consulta de nuevo antes de cada reporte. Sin cuenta activa o permiso `reports:write`, el trabajo permanece pendiente y no se genera el archivo.

También se movió `refresh(report)` antes del commit. Antes, un fallo de esa lectura posterior podía activar la limpieza del archivo cuando su registro ya estaba confirmado en la base.

No se añadieron columnas ni se ejecutaron migraciones. Se conservaron el cron UTC y el intervalo existente de consulta de cinco segundos.

## Verificación

Ocho casos en `backend/tests/test_scheduler_recovery.py`, usando SQLite y directorios temporales:

1. Fallo de generación: fecha original conservada, reintento correcto y siguiente consulta sin duplicar.
2. Cancelación simulada después de adquirir el trabajo: rollback al cerrar la sesión y reintento correcto.
3. Dos schedulers concurrentes: un único reporte persistido.
4. Primer trabajo fallido: otro trabajo del lote sí se procesa.
5. Propietario inactivo: ejecución pendiente.
6. Permiso del propietario revocado: ejecución pendiente.
7. Fallo simulado antes de confirmar la transacción: archivo retirado, ejecución pendiente y reintento correcto.
8. Fallo de refresh: sin registro confirmado ni archivo huérfano en este caso; reintento correcto.

Regresiones finales: **126 pruebas aprobadas, 7 omitidas y 7 subpruebas aprobadas**. Las omisiones requieren Docker Compose, no disponible en este equipo. Sintaxis de 58 archivos Python correcta; Bandit sin hallazgos medios/altos en los dos archivos de aplicación modificados. Diff sin errores de espacios.

Comando reproducible (usar una carpeta temporal nueva):

```powershell
.venv/Scripts/python.exe -m pytest backend/tests tests/test_prepare_deploy.py tests/test_ai_http.py -q --ignore=backend/tests/test_websocket_load.py --basetemp=tmp/scheduler-verificacion-nueva
```

## Alcance y pendientes

- Las pruebas de competencia y recuperación se ejecutaron en SQLite. Falta PostgreSQL y una terminación abrupta real del proceso; la cancelación probada es una simulación que cierra la sesión.
- Es una transacción de base de datos, no una transacción distribuida con el sistema de archivos. Una caída después de escribir el archivo y antes del commit puede dejar un archivo sin registro. Un corte de conexión durante el commit puede tener resultado incierto; este lote no acredita garantías absolutas entre BD y archivos.
- No se reconstruye un reporte por cada intervalo histórico perdido durante una parada larga. Se procesa la programación vencida y se calcula el siguiente cron desde el inicio de esa pasada.
- Una causa persistente de error seguirá reintentándose en las consultas sucesivas. No se incorporaron contador de intentos, backoff persistente ni cola de fallos; siguen siendo mejoras operativas pendientes.
- `last_run` solo se confirma cuando se persiste el reporte, pero su valor corresponde al inicio de la pasada. `Report.completed_at` identifica la terminación de la generación.
- No se modificó la instancia de exposición en ejecución, el servidor privado, sus datos ni sus imágenes. El proceso local ya iniciado debe reiniciarse para cargar el código nuevo; las pruebas ejecutaron la versión modificada de forma aislada.

El siguiente frente de QA sigue siendo permisos por rol y estados de usuarios, seguido del recorrido detecciones → alertas → reportes → auditoría. Mantener el trabajo del servidor y la integración PostgreSQL como verificaciones separadas.
