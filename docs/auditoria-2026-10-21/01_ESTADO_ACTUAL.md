# Informe 1 — Estado actual de AeroGuard

Fecha: 21-10-2026, America/Bogota. Base: `28c955f`; resultados después de correcciones locales identificados por separado.

## Resumen ejecutivo

AeroGuard permite demostrar un flujo académico de monitoreo: login, mapa, telemetría sintética, geocercas, alertas y exportaciones binarias. La API contiene persistencia real y control de roles, pero la interfaz demo utiliza sus propios datos. Procesar píxeles con OpenCV o Pillow no demuestra reconocimiento fiable de drones. No se encontró un conjunto de datos de evaluación, pesos entrenados ni métricas de clasificación de drones versionados.

El código base reprodujo sus **64 pruebas**, con **70,26 %** de cobertura de líneas frente al 70,21 % histórico. Después se añadieron 13 casos de regresión: 12 revelaron defectos y 1 fue control positivo. Se incorporaron otros 2 para límites de carga y formato. Corregidos los defectos, pasan **79 pruebas funcionales**, más **3 pruebas de carga** ejecutadas aparte. La cobertura queda en **72,28 %**, 1455 de 2013 instrucciones. Es evidencia de funcionamiento acotado, no certificación comercial.

## Integridad y procedencia

- Ruta del prompt `C:\AeroGuard`: ausente. Se usó el clon existente autorizado en `D:\aeroguard`.
- Rama `main`, remoto `JuanFe28/Aeroguard`, commit completo en el índice. Consulta `git ls-remote --heads --tags origin`: `main` coincide con `28c955f`; sin etiquetas anunciadas.
- Historial disponible: `076b0b6` (Plan/Code/Build, 15-10) y `28c955f` (TEST y correcciones, 19-10).
- Ya estaban eliminados localmente `INICIAR_EXPO_LUNES.bat` y `PLANIFICACIONMEJORA.md`; se preservó ese estado. El segundo se consultó con `git show HEAD:PLANIFICACIONMEJORA.md` sin restaurarlo.
- El JSON de Trello es una instantánea aportada por el usuario. Sus tarjetas no son órdenes de ejecución ni prueba de aceptación técnica. El extracto y hash están en `evidencias/trello-alcance.json`.

## Arquitectura que existe

| Componente | Implementación observada | Limitación |
|---|---|---|
| SPA MVVM | `frontend/src/{views,viewmodels,models}`, servicios y Leaflet | `frontend/index.html` activa demo; los mocks no son la BD |
| API | `backend/app/main.py`, routers FastAPI y Pydantic | Ciertos contratos del cliente no coinciden con los endpoints |
| Persistencia | SQLAlchemy asíncrono, PostgreSQL configurado y fallback SQLite | `init_db()` cae a SQLite ante errores; el arranque registra errores y `/health` sigue declarando healthy |
| Visión | Importación local de `ai_service/detector.py`; OpenCV o Pillow | No es una llamada HTTP al contenedor IA |
| Worker IA | Consumidor `ai.processing` en `detector.py` | El resultado se registra en log; actualización de detecciones sigue en TODO |
| Telemetría | Simulador → HTTP `/sensors/telemetry` → BD → WebSocket | Cada paquete crea una detección; no hay asociación temporal robusta de un mismo objeto |
| Geocercas | Ray-casting y rango de altitud en memoria | Hay generadores SQL y DDL PostGIS, pero las rutas no ejecutan `ST_Contains` |
| SOAR | POST a n8n opcional y reglas locales deterministas | Estado del dictamen en memoria; workflow necesita credenciales y callback autenticado |
| Despliegue | Cuatro Dockerfiles multi-stage y Compose | Configuración válida; imágenes y stack no ejecutados aquí |

La topología de colas descrita en `docs/PLANIFICACION_V1.1.md` no es el flujo completo ejecutado por el código: no se encontraron consumidores de telemetría/reportes en `backend/app/workers`, ni un planificador APScheduler inicializado. Tener esas dependencias instaladas no implementa esos servicios.

## Tecnologías y reproducibilidad

Python 3.11.9 y Node 24.19.0 en esta verificación. Dependencias directas destacadas: FastAPI 0.115.0, SQLAlchemy 2.0.36, Pydantic 2.9.2, OpenCV 4.10.0.84, Pillow 11.0.0, ReportLab 4.2.5, openpyxl 3.1.5, aio-pika 9.4.3 y websockets 13.1. Frontend Vanilla JS, Leaflet 1.9.4 y Web Audio API. Compose declara PostgreSQL 16 y RabbitMQ 3.13; no se verificó su ejecución.

Las dependencias directas tienen versiones mayormente fijas; varias de desarrollo y las transitivas no. `evidencias/entorno-instalado.txt` registra el entorno observado, incluyendo herramientas de auditoría. No es un lock universal ni una declaración de componentes de producción. `pip check` pasó. No se instaló Ultralytics ni se descargaron modelos.

## Inventario funcional verificado y parcial

| Funcionalidad | Estado real | Evidencia y pendiente |
|---|---|---|
| Login JWT y roles | Implementado y probado en SQLite | `security.py`, `auth.py`, tests de autenticación y regresiones; falta endurecimiento para usuarios reales |
| Usuarios | Crear/listar/detalle/estado en API | `users.py`; edición general que solicita el cliente no tiene endpoint equivalente |
| Cambio y recuperación de clave | Rutas presentes | `auth.py`, `email_service.py`; SMTP no probado; reset se imprime en log y carece de consumo único |
| Mapa y dashboard | Demo visual comprobada | Selenium: login, teselas, sensores, reportes; no prueba flujo completo de sensores reales |
| WebSockets | Transporte, JWT, ping/pong y broadcast probados | Carga con un servidor; memoria de conexiones por proceso |
| Telemetría y geocercas | Ingesta/alerta/persistencia local probadas | `sensors.py`, `geospatial_service.py`, `test_geospatial.py`; sensor_id no se asocia al registro y no hay tracking multiframe |
| Alertas | CRUD parcial y dictámenes | Cliente usa POST/`resolution_notes` para resolver; servidor exige PATCH/`notes`. Asignación también tiene diferencia cuerpo/query |
| Visión | Heurísticas de contraste, bordes y geometría | Imágenes sintéticas con rectángulo; inferencia de dron no validada |
| YOLO | Adaptador opcional, inactivo por defecto | Sin pesos ni dependencia en requirements; filtrado de clases corregido y probado con dobles de modelo |
| Reportes | PDF/XLSX válidos con datos sintéticos | `report_generator_service.py`, tests de exportación; filtros/BD no alimentan el dataset actual |
| Reportes por ID/CSV | Parcial | Descarga recompila según texto del ID, sin recuperar el archivo persistido; CSV solicitado cae a PDF |
| Programación de reportes | No implementada como servicio activo | Modelo y aviso en UI; sin scheduler operativo encontrado |
| Auditoría | Registros y verificación secuencial | Génesis corregido; aún sin anclaje externo, serialización concurrente ni detección fiable de truncamiento |
| PostGIS | Preparación parcial | Imagen `postgres:16-alpine` no aporta PostGIS; DDL tolera su ausencia; no hay sincronización de `geom` |
| Monitorización | Pendiente | `/health` es básico; sin instrumentación Prometheus/Grafana activa |

## Detección: lo que puede afirmarse

1. **Demo del navegador:** `AIService.analyzeImage` devuelve constantes; ahora se identifica como `Demo-Static`. Marcas/modelos de aeronaves mostrados en la demo son textos de ejemplo.
2. **OpenCV:** procesa píxeles y calcula contornos. Su score es heurístico y no una probabilidad calibrada. Un rectángulo oscuro puede producir un positivo.
3. **Pillow:** alternativa de bordes y caja envolvente. Antes respondía con nombre YOLO aunque no lo usaba; ahora declara `Pillow-Heuristic`.
4. **YOLO opcional:** antes aceptaba cualquier clase con alta confianza. Ahora exige nombres explícitos de dron. Las regresiones usan objetos simulados de resultado; no demuestran precisión de un modelo real.
5. **Telemetría:** antes guardaba `is_drone=true`, `ai_analyzed=true`, confianza 0.88 sin analizar imagen. Ahora registra ausencia de inferencia y no confirma dron.
6. **Dictamen local:** reglas de velocidad y altitud, no un LLM entrenado. Ahora `execution_source=embedded_rules`; ya no recomienda interferencia ni deduce intención hostil a partir de una sola lectura.

No hay métricas verificadas de precisión, recall, mAP, falsos positivos por hora, falsos negativos, distancia efectiva, noche/clima, hardware objetivo o latencia de inferencia de campo. El límite de 1500 ms del test es sobre una imagen sintética pequeña y no es un benchmark del producto. No existen capacidades demostradas de radar, RF, identificación del piloto o neutralización.

## Hallazgos y riesgos

| ID / prioridad | Evidencia concreta | Estado o acción |
|---|---|---|
| TEC-01 / P0 | `ai_vision_service.py`, `detector.py`: motor mal etiquetado y clases no filtradas | Corregido; validación de campo sigue pendiente |
| TEC-02 / P0 | `sensors.py`, `alerts.py`: escrituras operativas anónimas | Permisos añadidos; integrar token dedicado para simulador y n8n |
| TEC-03 / P1 | `audit_service.py`: génesis de escritura distinto al de verificación | Corregido con prueba válida y de manipulación |
| TEC-04 / P0 comercial | `reports.py` siempre usa `get_default_dataset()` | Etiquetas demo añadidas; conexión a BD, filtros y descargas por ID pendientes |
| TEC-05 / P0 público | `config.py`, `database.py`, `init.sql`: secretos de desarrollo y cuentas semilla conocidas | No se cambiaron credenciales; exigir bootstrap y configuración segura antes de exposición |
| TEC-06 / P0 público | `database.py` y `main.py`: fallback/errores sin readiness fiable | Diferenciar liveness/readiness y fallar cerrado fuera del modo académico |
| TEC-07 / P0 público | Avisos de dependencias en JSON de pip-audit | 65 avisos / 11 paquetes, pendientes de revisión; no actualizar mayores a ciegas |
| TEC-08 / P1 | `Dockerfile`: faltaban requirements transitivos de test y detector | Empaquetado corregido; construcción pendiente con motor Docker |
| TEC-09 / P1 | `websocket.py`, `_latest_verdict`, config mutable en memoria | Runtime reducido a un worker; fan-out distribuido y persistencia pendientes |
| TEC-10 / P1 | `api.service.js` vs rutas reales; `misc.views.js` usa mocks para histórico/auditoría | Crear pruebas de contrato y completar integración antes del MVP |
| TEC-11 / P0 público | `email_service.py` imprime enlaces reset; `auth.py` sin revocación real | No exponer correos/tokens; diseñar consumo único, revocación y rate limits |
| TEC-12 / P1 | `dashboard.viewmodel.js` interpola títulos/mensajes en `innerHTML` | Riesgo de XSS con entradas no confiables; requiere pruebas de escape antes de datos reales |
| TEC-13 / P1 | `frontend/index.html`: API/WS localhost, demo habilitada, clave de Maps en cliente | Configuración por entorno y restricciones de uso de clave; no se alteró la credencial |
| TEC-14 / P1 | Auditoría hasheada y reportes con SHA-256 | Hash de datos no equivale a firma digital, no repudio ni cadena de custodia acreditada |
| TEC-15 / P1 | `security.py`: truncamiento bcrypt a 72 bytes; reset no invalida tokens existentes | Política de contraseñas y sesiones requiere pruebas adicionales |

P0 público/comercial significa bloqueo para ese contexto; no impide mostrar una demo aislada con datos sintéticos. Son hallazgos de revisión y pruebas acotadas, no un pentest exhaustivo.

## Pruebas y límites

| Control | Resultado actual | Límite |
|---|---|---|
| Funcionales / integración | 79/79, 5,04 s | SQLite temporal, entorno development; parte de tests usa claims de demo |
| Cobertura | 72,28 % de líneas | No ramas, frontend, requisitos ni calidad de detección |
| Carga WS | 10/50/100 clientes: P95 3,240 / 13,168 / 35,295 ms | Ráfaga local: 8000 ping/pong, 1600 entregas, cero pérdidas; sin prueba prolongada |
| Bandit 1.9.4 | 0 altos, 0 medios, 23 bajos; sin errores | 37 archivos Python; no JavaScript, dependencias ni contenedores |
| Sintaxis | Python y 15 módulos JS aprobados | No equivale a lint completo; `npm run lint` ejecuta sintaxis |
| Selenium Edge | Recorrido demo aprobado | Capturas; sin prueba visual completa de todos los roles ni backend desde UI |
| Compose | `docker compose config --quiet`: 0 | Validación de configuración, sin build ni servicios |
| Postman / Gherkin | Archivos existentes inspeccionados; OpenAPI actual exportado | No se ejecutó colección Postman ni runner BDD en esta auditoría |

Los 23 bajos de Bandit: B311=13 (simulación aleatoria), B105=1 (`bearer`), B107=1 (token vacío opcional), B404=2, B603=4, B607=2 (subprocesos de lanzadores/verificador, sin shell; últimos dos requieren un PATH confiable). El escaneo completo devuelve 1 por bajos; el verificador aplica el criterio explícito de cero medios/altos. No se añadieron exclusiones de reglas.

## Madurez y siguiente umbral

**Madurez:** prototipo académico integrado en laboratorio. Como aproximación interna, compatible con TRL 3–4; no es una evaluación TRL certificada. No es aún un MVP de detección validada ni un piloto operativo.

Para un MVP de gestión de eventos: una fuente real autorizada, trazabilidad de origen, contratos UI/API consistentes, persistencia fiable, identidad de sensores, sesiones seguras y una prueba de operación. Para un MVP de detección visual se añaden dataset legal, anotaciones, separación por escenarios, modelo de drones, métricas y ensayo ciego en hardware y condiciones definidos. Para operar con clientes: dependencias revisadas, políticas de privacidad, titularidad/licencias, respaldo restaurado, soporte y contrato con limitaciones medibles.
