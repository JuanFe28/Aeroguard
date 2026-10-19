# TEST-01 — Pruebas unitarias y de integración del backend

Tarjeta: https://trello.com/c/CSwgdoTl

Resultado final del 19 de octubre de 2026: **64 pruebas aprobadas, 0 fallidas y 0 omitidas**. Cobertura de líneas de `backend/app`: **70,21 %** (1400 de 1994 instrucciones ejecutables), medida con pytest-cov. Tiempo de la suite: 9,47 s.

Se verificaron autenticación JWT, permisos por rol, análisis de imagen y rechazo de entradas inválidas, PDF/Excel, geoespacial, agente táctico, configuración y WebSockets funcionales. La suite incluye las 23 regresiones añadidas al corregir TEST-03. Las tres pruebas de carga se ejecutaron aparte para no alterar su latencia con el recolector de cobertura.

Evidencia: `TEST-01_evidencias.zip`. Extraer y abrir `htmlcov/index.html`, `pytest.xml` o `ejecucion.txt`.

Texto corto para Trello: «Suite del backend ampliada y ejecutada: 64/64 pruebas aprobadas, 0 fallos y cobertura de líneas 70,21 %. Se adjuntan resultados y reporte HTML de cobertura».

Alcance: SQLite temporal. El porcentaje no incluye frontend, Selenium ni Postman y no representa cobertura de ramas o requisitos. No certifica PostgreSQL/PostGIS, RabbitMQ ni precisión de reconocimiento de drones reales. El tablero exportado no establece un porcentaje mínimo; si la rúbrica exige uno mayor, deberá cumplirse antes de cerrar ese requisito.

Reproducir desde `C:\AeroGuard`:

```powershell
$env:COVERAGE_FILE = 'C:\AeroGuard\docs\evidencias\TEST-01\.coverage'
.\venv\Scripts\python.exe -m pytest backend/tests --ignore=backend/tests/test_websocket_load.py --basetemp=tmp/trello-repro-backend -v --cov=backend/app --cov-report=html:docs/evidencias/TEST-01/htmlcov --cov-report=json:docs/evidencias/TEST-01/coverage.json --cov-report=xml:docs/evidencias/TEST-01/coverage.xml --junitxml=docs/evidencias/TEST-01/pytest.xml
```
