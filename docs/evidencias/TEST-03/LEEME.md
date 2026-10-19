# TEST-03 — Análisis estático SAST

Tarjeta: https://trello.com/c/cYxORNGM

Resultado: **escaneo realizado y correcciones verificadas; sin avisos medios ni altos**. Bandit 1.9.4 analizó 36 archivos Python de `backend/app`, `ai_service`, `sensor_simulator` y `scripts`, sin errores de análisis. No es un escaneo de JavaScript ni una auditoría de dependencias o prueba de intrusión.

Antes: 26 avisos (3 medios, 23 bajos). Después: **0 altos, 0 medios y 17 bajos revisados**. Se conservan ambos JSON completos. No se añadieron `nosec` ni se omitieron reglas. El escaneo completo devuelve código 1 por los avisos bajos; el control explícito de severidad media/alta con `-ll` devuelve código 0.

Correcciones comprobadas:
- Tokens demo limitados a `development` con `DEBUG=true`; usuarios inexistentes o errores de BD no conceden acceso en producción.
- HTTP, WebSocket y renovación de tokens comparten la consulta de usuario activo. WebSocket rechaza refresh/reset y cuentas ausentes/desactivadas.
- Reportes con nombres exclusivos y directorio predeterminado por usuario: no se sobrescriben dentro del mismo segundo.
- Comprobaciones del lanzador limitadas a HTTP en 127.0.0.1, sin redirecciones ni esquemas alternativos.
- Excepciones de auditoría/broadcast registradas; manejadores de error corregidos y verificados.

Las **23 regresiones de seguridad aprobaron**, dentro de la suite final de 64 pruebas. Los intentos originales se reprodujeron antes de corregirlos. Se preservaron controles legítimos de JWT, demo, reportes y usuarios activos. El paquete contiene un resumen de esos fallos previos sin volcar tokens ni trazas completas.

Revisión de los 17 avisos bajos conservados:
- B311 (13): aleatoriedad de telemetría sintética; no genera claves ni credenciales.
- B105 (1): etiqueta literal `bearer`, no una contraseña.
- B107 (1): token opcional vacío; no es una credencial incorporada.
- B404/B603 (2): importación y llamada subprocess del lanzador; argumentos internos en lista, sin shell.

Texto corto para Trello: «SAST ejecutado y fallos reproducidos corregidos. Bandit: 0 avisos medios/altos; 17 bajos revisados y documentados. Las 23 regresiones de seguridad aprobaron dentro de 64 pruebas del backend».

Evidencia: `TEST-03_evidencias.zip`. Si un criterio externo exige cero avisos de cualquier severidad, este resultado conserva observaciones y no equivale a ese criterio más estricto.

Reproducir:

```powershell
.\venv\Scripts\python.exe -m bandit -r backend/app ai_service sensor_simulator scripts -f json -o docs/evidencias/TEST-03/bandit_despues.json
.\venv\Scripts\python.exe -m bandit -r backend/app ai_service sensor_simulator scripts -ll
```
