# Preparación de la siguiente candidata académica

Estado: cambios en `codex/qa-continuation`, PR #2 hacia `deploy/academic-vm`. No hay nueva release publicada ni actualización de las imágenes del servidor. Se propone `1.2.0-rc.2` cuando se acepte el lote; no se cambian ahora los metadatos ni se reutiliza la etiqueta rc.1.

## Cambios preparados

- Configuración cargable/guardable, sensores que conservan su estado al editar y formularios que mantienen los datos ante errores.
- Perfil consultable; mapas de zonas/trayectorias con atribución OSM; trayectorias con detalle de puntos y estados de ausencia/error/muestra única.
- SOAR sin incidente inicial inventado ni telemetría ficticia de respaldo; reglas locales identificadas como experimentales.
- Reportes programados y avance del cron en una transacción, con regresiones de reintento, competencia y permisos.
- UUID canónicos y referencias verificadas antes de consultar/persistir; paginación acotada y notas de resolución obligatorias.
- Detección manual con geocerca validada antes de generar una alerta y persistencia conjunta de detección/punto/alerta.
- Roles y sesiones probados con usuarios persistidos y login real; recorrido integrado hasta reporte original y auditoría.
- TXT para el portátil autorizado, Compose privado de Monitor, preparación idempotente de secretos y stack QA separado.

## Compatibilidad

Clientes que envían IDs arbitrarios o referencias inexistentes recibirán errores 422/404. `null` explícito se rechaza en campos obligatorios de actualización de sensores/zonas; omitir conserva el valor. La resolución exige texto no vacío. No solicitar más de 500 resultados por página en las listas acotadas.

No se añaden tablas ni columnas en este lote. La fecha de telemetría enviada por el sensor se conserva como UTC; el adaptador debe definir reloj, unidades y referencia vertical. La visualización sigue siendo 2D y no hay validación independiente de visión.

## Puertas antes de publicar

1. Revisar el diff del PR #2 y los resultados de Actions del HEAD final.
2. Construir y ensayar las imágenes del código nuevo en Linux con PostgreSQL/PostGIS, usando el stack de QA del TXT.
3. Ejecutar [la aceptación del servidor](ACEPTACION_SERVIDOR.md) y resolver fallos observados; conservar evidencia de recuperación y controles de acceso.
4. Revisar y aceptar la identificación rc.2; alinear API, `.env.example`, Python, frontend, package y notas en un único cambio de versión.
5. Publicar imágenes nuevas con digests y commit trazables; actualizar el manifiesto de despliegue a esos digests después de verificarlos.
6. Preparar respaldo y retorno, actualizar el destino autorizado y comprobarlo. No fusionar automáticamente el PR #1 ni sobrescribir una etiqueta publicada.

Los pasos 2, 3 y 6 requieren el servidor/equipo Docker autorizado. Las decisiones de aceptación y publicación siguen pendientes del responsable; no se sustituyen por un conteo de pruebas aprobadas.
