# Auditoría de AeroGuard · 18 de noviembre de 2026

Revisé la candidata académica `1.2.0-rc.2` en `main`, en el commit `23d276cf698045bf411eb48abaf27580733097e9`. El checkout original tenía 23 commits menos. La versión publicada en GHCR se construyó desde `6c38df58418b65bc3a73391edd70ab30c3e88b34`, como registra el manifiesto de imágenes. Verifiqué las ejecuciones de GitHub para ambos commits. [Comparación con el checkout inicial](https://github.com/JuanFe28/Aeroguard/compare/2f1971f...23d276c) · [CI de main](https://github.com/JuanFe28/Aeroguard/actions/runs/43078100579) · [Publicación de rc.2](https://github.com/JuanFe28/Aeroguard/actions/runs/43075746836)

## Prompt utilizado

> Localiza AeroGuard en mi GitHub y contrasta la rama principal con la copia local. Revisa la arquitectura, el código, la configuración, las dependencias, las pruebas y los flujos de compilación y despliegue. Busca errores reproducibles y fallos potenciales en permisos, entradas, datos, estados y manejo de errores. Prioriza los hallazgos por impacto y susténtalos con archivos, líneas o resultados de pruebas. Corrige los problemas verificables dentro del alcance de la aplicación, respeta los cambios que ya estén en curso y vuelve a ejecutar las comprobaciones disponibles. Entrega un resumen de lo corregido, la evidencia de validación y cualquier requisito pendiente para operar o desplegar la app.

## Correcciones

| Prioridad | Hallazgo | Corrección |
| --- | --- | --- |
| Alta | Un cambio de contraseña o cierre de sesión concurrente podía hacer que un inicio o una renovación emitiera un JWT con la versión nueva a partir de una autenticación anterior. | El inicio lee el hash y la versión en una misma consulta. La renovación conserva la versión que validó. |
| Alta | Nginx registraba la URL completa del WebSocket. Conté 50 entradas con el parámetro de sesión en el ensayo inicial. | El registro de acceso conserva ruta, método, estado y tamaño, y omite la consulta. Para WebSocket, el registro de errores se limita a los críticos porque el proxy puede incluir la URL original en sus diagnósticos. |
| Alta | Las restricciones de dependencias fijaban versiones con avisos en `dnspython` y `opentelemetry-api`. Un entorno Python 3.11 recién creado también traía una versión antigua de `pip`. | Actualicé las dos restricciones e hice explícita la actualización de `pip` en los trabajos que auditan o publican. |
| Media | Las exportaciones de alertas omitían las alertas manuales y podían mostrar la fecha de la detección en un reporte filtrado por fecha de alerta. | CSV, Excel y PDF usan la alerta como registro principal. El identificador corresponde a la alerta y el CSV y el Excel conservan la referencia a la detección cuando existe. Los datos de telemetría ausentes se muestran vacíos o como «Sin datos». |
| Media | Un canal WebSocket podía entregar actualizaciones de sensores sin comprobar el permiso de lectura de sensores. Un mensaje JSON con un valor simple también podía interrumpir el canal. | El envío aplica `sensors:read` y el canal descarta de forma segura mensajes JSON que no representan un objeto. |
| Media | El servicio de imágenes independiente no convertía toda excepción esperada por dimensiones excesivas en un error de entrada. | El endpoint responde con HTTP 400 cuando Pillow rechaza la imagen por sus dimensiones. |
| Media | En zonas, las etiquetas blancas sobre naranja tenían un contraste de 2,82:1 frente al mínimo de 4,5:1. El ajuste automático del mapa también descartaba coordenadas en el ecuador o meridiano cero. | Las etiquetas usan fondo oscuro y borde de severidad. La cámara del mapa y el detalle de alertas admiten coordenadas finitas, incluido cero. |
| Media | El ensayo PostgreSQL consumía el límite de inicios de sesión al simular muchos usuarios desde una IP. | La configuración exclusiva de QA usa el mismo límite que el ensayo SQLite. La configuración privada de despliegue mantiene su valor de producción. |
| Media | El flujo de publicación inspeccionaba y probaba una etiqueta mutable después de subir la imagen. | La verificación usa la referencia por digest. GitHub serializa las ejecuciones para una misma versión. |
| Baja | El linter de JavaScript fallaba con 17 errores de configuración o bloques de recuperación vacíos. | Registré las API del navegador, documenté las recuperaciones y añadí el linter y la prueba del servicio HTTP a CI. Quedaron nueve avisos de variables o argumentos sin uso. |

[Aviso de dnspython](https://github.com/advisories/GHSA-vvf4-9x63-8xvv) · [Aviso de OpenTelemetry](https://github.com/advisories/GHSA-mf5v-w3w3-f6cg)

[Sesiones](../../backend/app/api/v1/endpoints/auth.py#L156) · [Permisos WebSocket](../../backend/app/api/v1/endpoints/websocket.py#L72) · [Registro del proxy](../../nginx.conf#L1) · [Consulta de reportes](../../backend/app/services/report_data_service.py#L19) · [Configuración de QA](../../deploy/compose.source-qa.yml#L9)

## Evidencia local

| Comprobación | Resultado |
| --- | --- |
| Python en un entorno nuevo | 186 pruebas funcionales y auxiliares aprobadas, más 10 subpruebas. La prueba nueva verifica una alerta manual en los tres formatos y su filtro de fecha. |
| Cobertura | 74,8 % de las líneas ejecutables de `backend/app`. Las rutas de sensores, imágenes y arranque de base están por debajo del 50 % en esa ejecución de cobertura. |
| WebSocket | Tres escenarios aprobados por separado. Con 100 clientes, P95 de 74,47 ms, 1.000 entregas de eventos y cero pérdidas. Al ejecutar con cobertura y Chromium simultáneos, el P95 subió a 121,42 ms. El objetivo del repositorio es 100 ms. |
| Navegador con SQLite | 51 casos aprobados en Chromium, con escritorio, tablet y móvil. |
| Navegador con PostgreSQL | 51 de 51 casos aprobados detrás de Nginx después de corregir el contraste y la configuración de QA. Revisé muestras visuales de escritorio y móvil. La aceptación final de interfaz del proyecto sigue pendiente. |
| Registros de Nginx | Después del cambio, `nginx -t` y seis recorridos de navegador aprobados. El registro conservó seis conexiones WebSocket con estado 101 y ninguna entrada con el parámetro de sesión. |
| Paquetes | `pip check` consistente. `pip-audit` y `npm audit` sin avisos conocidos en los entornos revisados. |
| Análisis estático | Sintaxis de 61 archivos Python y 16 módulos JavaScript; 11 pruebas JavaScript aprobadas. Bandit registró 56 avisos bajos sin avisos medios o altos ni errores de análisis. |
| Docker | Construcción local de las cuatro imágenes. Nginx, FastAPI en modo producción, PostGIS 3.5 y RabbitMQ arrancaron en el proyecto privado `aeroguard-audit`. El ensayo básico verificó autenticación y revocación de la sesión. |
| Cola y servicio de imágenes | Cinco pruebas HTTP aprobadas dentro de la imagen Docker y un trabajo sintético de RabbitMQ persistido en PostgreSQL. El módulo simulador importó correctamente en su imagen. |
| Observabilidad | Prometheus registró el destino `aeroguard` como `up`. Grafana sirvió el dashboard con sus cuatro paneles provisionados. |
| Respaldo | Restauración del dump en una base nueva y verificación de conteos. El hash del reporte respaldado coincidió con el archivo descargado de la API. |

## Continuidad

El código se guarda en la rama `codex/auditoria-2026-11-18`, basada en `main` en `23d276c`. Esta rama permite retomar la revisión y abrir el PR cuando se decida integrar. La versión del ensayo local se identificó como `1.2.0-qa.revision-20261118`.

Para repetir el ensayo, consulta [la guía de despliegue y QA](../../deploy/README.md). Usa datos sintéticos y credenciales generadas para ese entorno.

## Riesgos pendientes y medidas preventivas

| Prioridad | Riesgo | Medida antes de operar |
| --- | --- | --- |
| Alta para operación física | El motor visual es experimental. La minería de datos usa etiquetas sintéticas y ajusta el escalador antes de separar entrenamiento y prueba. Las métricas de ese módulo no constituyen evidencia de desempeño con drones reales. | Corregir la metodología de evaluación experimental y exigir validación independiente de sensores, condiciones y datos antes de tomar decisiones operativas. |
| Alta para despliegue | La versión corregida está construida localmente. Los digests de GitHub corresponden a la rc.2 anterior a esta auditoría. | Integrar el parche y construir una nueva candidata con trazabilidad de los cuatro digests. Para actualizar el destino real se requiere acceso autorizado y respaldo previo. |
| Alta en instalaciones previas | El proxy de la versión publicada puede haber conservado parámetros de sesión en sus registros. | Revisar permisos y retención de esos registros. Si contienen sesiones activas, revocarlas mediante el procedimiento de operación del servidor. |
| Media | La API de telemetría admite reenvíos y marcas de tiempo fuera de orden. En una red intermitente, una muestra antigua puede actualizar la posición mostrada y los reenvíos pueden sumar puntos. | Acordar una clave de muestra por sensor y comprobar orden e idempotencia con datos sintéticos antes de conectar hardware. |
| Media | La protección del último administrador cuenta usuarios activos antes de confirmar la modificación. Los cambios simultáneos requieren una comprobación transaccional. | Añadir una regresión de concurrencia de administración sobre PostgreSQL y serializar los cambios que puedan retirar el último acceso administrativo. |
| Media | La pantalla de mapas y sus fuentes dependen de terceros. Las integraciones de correo y automatización externa dependen de la configuración de cada destino. | Definir el comportamiento sin Internet y verificar recuperación por correo y receptores externos en el entorno autorizado. |
| Media | La carga WebSocket depende de los recursos compartidos y el presupuesto del servidor. | Ejecutar las pruebas de capacidad por separado y medirlas en el destino con su perfil real de CPU, memoria y clientes. |
| Baja | Con varios polígonos en el mismo centro, las etiquetas se superponen. Ya se observa en el ensayo con zonas sintéticas coincidentes. | Probar un mecanismo de selección o agrupación de etiquetas en la siguiente revisión visual. |

[Arquitectura del proyecto](https://github.com/JuanFe28/Aeroguard/blob/23d276cf698045bf411eb48abaf27580733097e9/docs/tecnica/ARQUITECTURA.md) · [Metodología de minería](https://github.com/JuanFe28/Aeroguard/blob/23d276cf698045bf411eb48abaf27580733097e9/docs/MINERIA_DATOS_CRISP_DM.md) · [Aceptación del servidor](https://github.com/JuanFe28/Aeroguard/blob/23d276cf698045bf411eb48abaf27580733097e9/docs/qa-2026-10-29/ACEPTACION_SERVIDOR.md)
