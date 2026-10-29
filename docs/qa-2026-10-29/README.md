# Continuación de QA — 29 de octubre de 2026

## Estado final de la entrega preparada

La rama `codex/qa-continuation` está publicada en GitHub y se revisa en el [PR #2](https://github.com/JuanFe28/Aeroguard/pull/2), dirigido a `deploy/academic-vm`. El PR #1 y producción conservan su revisión independiente. Los apartados siguientes registran sesiones anteriores; este estado tiene prioridad sobre sus referencias a cambios locales o pendientes ya resueltos.

Verificación final local: **175 pruebas aprobadas, 7 omitidas por falta de Docker Compose y 7 subpruebas aprobadas; 10 pruebas frontend aprobadas**. Sintaxis de 61 archivos Python y 16 JavaScript correcta; Bandit de `backend/app` sin hallazgos medios/altos. Se ejecutaron con Python 3.12, SQLite temporal y usuarios de prueba. Las tres pruebas de carga conservan su evidencia anterior y no forman parte de ese conteo funcional.

Se añadió aceptación integrada de telemetría → detección → trayectoria → alerta asignada/resuelta → CSV original con hash → auditoría, con usuarios persistidos, login real y controles de permisos. También se validan UUID, referencias existentes, límites numéricos y paginación; los campos obligatorios de sensores/zonas no admiten `null` explícito. La detección manual comprueba la geocerca antes de crear una alerta y confirma detección, punto y alerta juntos. El techo de cero metros conserva su significado.

La recuperación del scheduler y las trece regresiones de roles/estados ya están implementadas y verificadas localmente. La aceptación visual completa, PostgreSQL, construcción de imágenes nuevas y ejecución en el destino siguen pendientes. Los checks `checks`, `handoff-layout` y `rehearsal` aprobaron para el checkpoint `9453997`; consultar el HEAD final del PR antes de ejecutar. `rehearsal` ensaya las imágenes publicadas de rc.1; la construcción manual de contenedores está omitida en las ejecuciones de PR.

Para continuar: [comandos del portátil](../../COMANDOS_SERVIDOR_CASA.txt), [aceptación y evidencias del servidor](ACEPTACION_SERVIDOR.md), [siguiente candidata](SIGUIENTE_CANDIDATA.md), [manual de operación actualizado](../correcciones-2026-10-21/OPERACION.md) y [estado de Trello](ESTADO_TRELLO.md). El servidor apagado no recibió cambios y el tablero no se modificó.

## Historial de sesiones anteriores

Último lote: [recuperación del scheduler](SCHEDULER_RECUPERACION.md), con ocho regresiones nuevas. Verificación acumulada: 126 pruebas funcionales aprobadas, 7 omitidas por falta de Compose; frontend sin cambios en ese lote.

Actualización posterior: revisión y mejoras del módulo de trayectorias y matriz de entidades reguladoras en [TRAYECTORIAS_Y_AUTORIDADES.md](TRAYECTORIAS_Y_AUTORIDADES.md). Última verificación: 118 pruebas funcionales y 10 frontend aprobadas; 7 pruebas de Compose omitidas. Las cifras inferiores corresponden a las sesiones anteriores.

Rama local: `codex/qa-continuation`, basada en `origin/deploy/academic-vm` (`a884c39`). Se retomaron los fallos del informe del 28 de octubre. Cambios locales, pendientes de revisión, publicación y despliegue. El servidor conserva sus imágenes anteriores.

## Correcciones

- Configuración: el checkbox renderizado coincide con el usado al cargar, guardar y restablecer. Su etiqueta describe el análisis experimental de IA.
- Sensores: editar omite el estado para conservarlo; crear/editar/activar actualiza los contadores. Latitud, longitud, altitud y alcance tienen límites HTML; se conservan coordenadas cero.
- Usuarios: un error al guardar mantiene abierto el formulario y conserva sus valores. El envío se deshabilita mientras espera respuesta.
- SOAR: el estado inicial carece de incidente, objetivo o amenaza inventados. La API exige telemetría y zona explícitas con límites numéricos. El dashboard requiere una detección y su zona activa, conserva ceros y confianza desconocida y usa el techo configurado de esa zona. Las reglas locales se identifican como experimentales.
- Sirena y alertas: se usa el método existente `Toast.warn`.
- Zonas: se rechazan rangos de altitud incoherentes, coordenadas incompletas y activación sin tres vértices distintos. La validación también considera valores existentes al actualizar parcialmente. Las zonas nuevas del formulario son borradores inactivos; guardar su polígono las activa. Los errores de guardado mantienen el formulario. Coordenadas sobre el ecuador o meridiano cero se normalizan correctamente.
- Identificación: login y package.json coinciden con la candidata 1.2.0-rc.1. Esto no publica una versión nueva.
- CI: se incorporó la ejecución de las regresiones del frontend sin dependencias npm adicionales.

## Verificación local

Entorno aislado `.venv`, Python 3.12.14, SQLite temporal; sin acceso SSH ni cambios del servidor.

| Control | Resultado |
|---|---|
| Backend + preparación de despliegue + adaptador HTTP | 116 aprobadas, 7 omitidas, 7 subpruebas aprobadas |
| Motivo de las 7 omisiones | Falta Docker Compose en este equipo; no se ejecutaron esas comprobaciones |
| Frontend: handlers reales con dobles de DOM y servicios | 6 aprobadas |
| Carga TCP/WebSocket: 10, 50 y 100 clientes | 3 aprobadas; P95 de 4,104 / 16,199 / 33,223 ms; cero errores y pérdidas |
| Sintaxis | 56 Python y 16 JavaScript sin errores |
| Bandit, tres archivos de backend modificados | Sin hallazgos medios/altos |
| Diff | Sin errores de espacios |

Evidencia de carga: [websocket-load.json](websocket-load.json). La prueba usa el router y gestor reales en un servidor local aislado. No incluye la instalación PostgreSQL ni acredita capacidad del destino real. El resultado favorable de este equipo no resuelve por sí mismo la latencia del portátil anterior.

Comandos reproducibles (usar una carpeta temporal nueva para conservar evidencias):

```powershell
.venv/Scripts/python.exe -m pytest backend/tests tests/test_prepare_deploy.py tests/test_ai_http.py -q --ignore=backend/tests/test_websocket_load.py --basetemp=tmp/qa-nueva
node --test tests/frontend_qa.test.js
.venv/Scripts/python.exe -m pytest backend/tests/test_websocket_load.py -q --basetemp=tmp/carga-nueva
node scripts/check_js_syntax.js
.venv/Scripts/python.exe scripts/check_python_syntax.py
```

## Estado remoto verificado

En `a884c39`, [verificación académica](https://github.com/JuanFe28/Aeroguard/actions/runs/40706149061) y [ensayo de despliegue](https://github.com/JuanFe28/Aeroguard/actions/runs/40706149053) aprobaron; la construcción manual de contenedores figura omitida. Estos checks corresponden al punto anterior, no a las correcciones locales de este informe.

## Pendientes

1. Completar la revisión en navegador: los recorridos comprobados más abajo no cubren toda la aplicación. Faltan estados de usuarios, permisos por rol, detecciones, alertas, trayectorias, reportes, historial, auditoría y recuperación de contraseña.
2. El mapa de zonas y Perfil se corrigieron y verificaron en navegador, como se detalla más abajo.
3. Probar las nuevas validaciones en PostgreSQL. Crear borrador → dibujar → activar ya se comprobó en navegador con SQLite. La validación de vértices no sustituye una comprobación de topología completa de polígonos.
4. Revisar recuperación/reintentos del scheduler y UUID/referencias inválidas; no quedaron resueltos en este lote.
5. Publicar la rama de correcciones y verificar sus checks antes de integrar. El PR #1 conserva su revisión independiente y no se fusionó.
6. Preparar otra candidata con imágenes nuevas antes de actualizar el servidor; conservar etiquetas publicadas, secretos y volúmenes.
7. Medir carga en el destino autorizado y revisar la latencia del equipo anterior. SMTP, n8n externo, notificaciones, sensores físicos, validación independiente de visión y anclaje externo de auditoría siguen pendientes.

El informe del 28 de octubre y sus 50 resultados originales se conservan sin reclasificarlos como aprobados.

## Segunda sesión: verificación en navegador local

Se inició `scripts/expo_local.py` sobre `127.0.0.1:3000` y API `127.0.0.1:8000`. Base de exposición en `tmp/expo/aeroguard.db`, con cuentas y zonas sintéticas. No se accedió al servidor privado ni se probaron sensores físicos.

Comprobaciones realizadas:

- Inicio de sesión con el administrador de exposición; dashboard sin incidente inicial registrado.
- Configuración: se guardó altitud 900 m e IA desactivada; ambos valores sobrevivieron a una recarga. Luego se restablecieron y guardaron los valores predeterminados.
- Sensor: creación en latitud/longitud cero, contador de inactivos actualizado, activación y edición del nombre a `QA-LOCAL-EDITADO`. Conservó estado activo y contador de activos 1. Captura: [sensor-activo-editado.png](sensor-activo-editado.png).
- Zonas: el rango 300/100 mantuvo abierto el formulario. Se corrigió a 0/100, creó `QA-ZONA-LOCAL` inactiva, dibujaron tres vértices y guardó el polígono. Quedó activa y persistió al recargar/navegar.
- Usuarios: se intentó editar el operador sintético con un correo duplicado. La API indicó «El correo ya está registrado» y se conservaron formulario y nombre escrito. Al restaurar su correo original, guardó el nombre `QA Carlos Operador` y cerró el formulario correctamente.
- Perfil: el botón no tenía handler; se añadió un diálogo de consulta de identidad, accesible con teclado y con cierre por Escape. Se verificó que abre y muestra la identidad del administrador sintético.

Se reprodujo visualmente `API KEY REQUIRED` en las teselas CARTO. Se reemplazó la capa de zonas por el servicio estándar HTTPS de OpenStreetMap, con atribución visible y caché del navegador, conforme a su [política de uso](https://operations.osmfoundation.org/policies/tiles/). No se hicieron descargas masivas ni precarga de mapas. Se verificó la carga de las teselas y el mapa visible. Capturas: [zona-activa-mapa.png](zona-activa-mapa.png), [perfil-mapa.png](perfil-mapa.png).

Verificación tras este lote: **7 pruebas frontend aprobadas**, sintaxis de 16 módulos JavaScript correcta y `git diff --check` limpio. Las cifras de backend y carga de la primera sesión se conservan; no se repitieron al cambiar únicamente interfaz y pruebas frontend.

La instancia local queda disponible para continuar. Los datos sintéticos se conservan en su BD local ignorada por Git. El acceso web sigue limitado al equipo local. No se publicaron estos cambios ni se actualizaron imágenes del servidor.
