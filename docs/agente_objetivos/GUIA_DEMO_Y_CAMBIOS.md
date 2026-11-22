# AeroGuard — Demostración y cambios del agente basado en objetivos

**Rama:** `feature/agente-objetivos`. **Alcance:** prototipo académico y evaluación con datos sintéticos.

## Qué se implementó

1. Se agregó `goal_based_agent.py`, motor determinista que aplica cuatro objetivos explícitos: vigilar, priorizar revisión, evitar alarmas críticas sin evidencia suficiente y justificar decisiones.
2. El servicio `ai_tactical_agent_service.py` incluye `goal_decision` en la respuesta y en el evento WebSocket. En modo local, toma la gravedad del resultado del modelo (`CRITICAL` / `MEDIUM` / `LOW` / `UNKNOWN`), evitando contradicciones entre decisión y dictamen.
3. El endpoint autenticado `POST /api/v1/alerts/trigger-incident` invoca la evaluación; `GET /api/v1/alerts/ai-verdict` recupera la última decisión en memoria, con evidencia, explicación y origen. No se crea automáticamente una fila persistente en la tabla de alertas.
4. El Dashboard incluye un panel «MODELO BASADO EN OBJETIVOS», que muestra acción, prioridad, explicación, evidencias y necesidad de revisión humana. No interpreta HTML procedente de la API.
5. Se añadieron pruebas HTTP para tres escenarios y dos pruebas de presentación del panel, incluyendo evidencia tratada como texto. Se conservan las cinco pruebas aisladas originales y la suite preexistente.
6. Se mantienen `scripts/evaluar_agente_objetivos.py` y las tres gráficas en `docs/agente_objetivos/resultados/`.

## Guion de demostración (solo datos de prueba)

1. Iniciar la exposición local de AeroGuard siguiendo el README. Usar el usuario de demostración definido para una base nueva; nunca compartir credenciales reales ni secretos.
2. Entrar al Dashboard con el backend activo y los permisos `alerts:read` y `alerts:write`.
3. Seleccionar un objeto de muestra y una zona en la interfaz. Pulsar **Disparar SOAR**; esta acción envía un evento de prueba al endpoint autenticado.
4. Mostrar el dictamen y, debajo, la **decisión del agente basado en objetivos**, la evidencia numérica y la obligación de revisión humana. La decisión también puede consultarse desde `GET /api/v1/alerts/ai-verdict` y el evento `ai_verdict` de WebSocket.
5. Explicar los tres escenarios esperados (pruebas automatizadas):
   - Altitud **135 m** frente a límite **120 m**, confianza **0.95** → `NOTIFICAR_Y_VERIFICAR`, prioridad `CRITICAL`.
   - Mismo evento con confianza **0.20** → `VERIFICAR_DETECCION`, prioridad `REVIEW` / severidad visual `MEDIUM`.
   - Altitud **80 m** frente a límite **120 m** → `MONITOREAR`, prioridad `NORMAL` / severidad visual `LOW`.
6. Abrir `docs/agente_objetivos/resultados/01_efectividad.png`, `02_tiempos.png` y `03_decisiones.png` y explicar los datos de muestra.

## Verificaciones para un compañero

En PowerShell, desde `C:\AeroGuard` y con el entorno virtual ya preparado:

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m pytest -q backend/tests
node --check frontend/src/viewmodels/dashboard.viewmodel.js
node --check frontend/src/views/dashboard.view.js
node --test tests/goal_agent_ui.test.js
.\.venv\Scripts\python.exe scripts/evaluar_agente_objetivos.py
```

Para verificar por HTTP el circuito completo hace falta un entorno local con backend arrancado, sesión con permisos y una instalación de desarrollo funcional. Si n8n está activado y devuelve un dictamen, este conserva su propio origen; las recomendaciones del agente aparecen separadas.

## Limitaciones importantes

- Los **153 casos son sintéticos**; el 100 % de concordancia refleja reglas de referencia definidas para el experimento, no la precisión de detección de drones.
- Este agente implementa una **política basada en objetivos explícitos**; no realiza búsqueda de rutas ni planificación probabilística, ni aprende de forma automática.
- El umbral de altitud **no demuestra por sí solo** invasión geográfica ni identifica objetos, intenciones o autorizaciones.
- La última decisión se almacena **en memoria de un proceso**, no en historial persistente; un reinicio puede borrarla.
- En el modo local, `ai_verdict` es un resumen explicativo y `threat_level` una etiqueta de prioridad para el panel; no acredita amenaza real.
- No se han validado sensores físicos, rendimiento extremo a extremo ni una demostración de navegador real en todos los sistemas.
- El motor no genera automáticamente una nueva fila `Alert` en PostgreSQL, aunque permite emitir un evento WebSocket `ai_verdict`.

## Explicación breve para el profesor

> Escogimos un **agente basado en objetivos** porque AeroGuard no solo debe reaccionar a valores, sino decidir si conviene monitorear, verificar una detección o avisar al responsable según los datos disponibles. El sistema conserva las evidencias de cada decisión y exige revisión humana. Las gráficas permiten comparar esta política con un agente reactivo simple; son resultados controlados de laboratorio, no una afirmación de precisión con drones reales.
