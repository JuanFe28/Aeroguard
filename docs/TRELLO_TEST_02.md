# TEST-02 — Carga concurrente de WebSockets

Tarjeta: https://trello.com/c/maKUw5ql

Resultado: **3/3 escenarios aprobados** por TCP/WebSocket real en un puerto efímero local. Se usa el router y ConnectionManager de la aplicación, autenticación JWT de un usuario de la SQLite temporal y un servidor separado del de exposición.

| Clientes simultáneos | Pares ping/pong | Broadcasts entregados | P95 RTT (ms) | Máximo RTT (ms) | Resultado |
|---|---|---|---|---|---|
| 10 | 500 | 100 | 7.181 | 8.807 | PASSED |
| 50 | 2500 | 500 | 27.278 | 49.671 | PASSED |
| 100 | 5000 | 1000 | 50.861 | 81.551 | PASSED |

Se comprobaron 8.000 pares ping/pong y 1.600 entregas de detecciones en total. Todos los mensajes conservaron su identificador; no hubo pérdidas, duplicados, errores ni conexiones pendientes al terminar.

Criterios locales declarados antes de medir: clientes simultáneos completos, cero pérdidas/errores, cierre limpio y P95 de ida y vuelta inferior a 100 ms. La prueba es una carga acotada de ráfagas y no establece la capacidad máxima ni estabilidad prolongada de una instalación de producción.

Texto corto para Trello: «Carga WebSocket validada con 10, 50 y 100 clientes simultáneos; 3/3 escenarios aprobados, cero pérdidas y conexiones liberadas. A 100 clientes, P95 = 50.861 ms, inferior al objetivo local de 100 ms».

Evidencia: `TEST-02_evidencias.zip`, con `resultados.json`, `pytest.xml` y `ejecucion.txt`.

Reproducir desde `C:\AeroGuard`:

```powershell
.\venv\Scripts\python.exe -m pytest backend/tests/test_websocket_load.py --basetemp=tmp/trello-repro-carga -v -s --junitxml=docs/evidencias/TEST-02/pytest.xml
```
