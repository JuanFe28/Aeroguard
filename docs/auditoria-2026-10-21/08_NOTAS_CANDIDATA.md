# Notas de candidata académica — borrador local

Fecha: 21-10-2026. **Sin tag, sin publicación y sin aprobación de Release.** Base Git `28c955f`; cambios de auditoría aún en árbol de trabajo. Identificación interna conservada: 1.1.0. Sugerencia a discutir: `v1.1.1-rc.1`, sin asignarla todavía.

## Problema y cambios

La base académica pasaba sus pruebas, pero permitía escrituras operativas anónimas y presentaba resultados heurísticos o sintéticos con etiquetas que podían interpretarse como IA validada. La candidata exige permisos en esas rutas, identifica motores reales, filtra clases YOLO explícitas, rechaza imágenes inválidas y muestra el carácter sintético de la demo y reportes. La verificación de auditoría usa el mismo origen de cadena que su escritura.

Se prepararon ajustes de empaquetado y persistencia de reportes, un verificador reproducible, CI y construcción manual de imágenes sin publicación. El runtime de backend usa un worker por el estado WebSocket y dictámenes en memoria. Se retiraron recomendaciones locales de interferencia y atribuciones de intención no sustentadas.

## Compatibilidad a revisar

- Telemetría y dictámenes requieren Bearer y permisos; adaptar simulador y n8n antes de ensayarlos.
- `engine` informa OpenCV, Pillow, YOLO opcional o demo; clientes no deben exigir la etiqueta histórica `YOLOv8n-OpenCV-Real`.
- `model_validated=false` y `confidence_kind` evitan interpretar scores como precisión acreditada.
- Una lectura de telemetría sin imagen no genera una supuesta confirmación visual.
- El Dockerfile backend se construye desde la raíz con `-f backend/Dockerfile`.

## Verificación disponible

- Base reproducida: 64 pruebas, 70,26 % de cobertura en este entorno.
- Correcciones: 79 pruebas funcionales, 72,28 % de cobertura de líneas.
- Carga: 3 escenarios con 10/50/100 clientes, sin pérdidas en ráfaga local.
- Bandit: 0 altos/medios, 23 bajos conservados y descritos.
- Sintaxis Python/JS y configuración Compose válidas.
- Edge sin ventana: login demo, mapa, sensores y reportes comprobados.

Evidencias definitivas: `evidencias/cierre`, `evidencias/selenium-cierre*` y `evidencias/compose-config.txt`. Los XML/JSON vinculan los resultados al código local; para distribuir, congelar el commit definitivo y volver a registrar el manifiesto.

## Limitaciones y bloqueos de distribución

Visión sin modelo/dataset/métricas de campo; reportes con datos sintéticos; integración frontend/API incompleta; PostGIS y worker IA parciales; programador de reportes y observabilidad pendientes. Las cuentas de laboratorio y configuración actual no son aptas para exposición pública. Faltan build/smoke de imágenes, restauración de backups y revisión de dependencias (65 avisos en 11 paquetes del entorno). No se ejecutaron pruebas PostgreSQL, RabbitMQ, n8n, Postman o BDD.

No se reclama certificación de seguridad, firma digital de reportes, cadena de custodia acreditada ni preparación comercial. La aceptación académica debe incluir estos límites y contrastarse con la rúbrica docente.
