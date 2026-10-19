# AeroGuard — Guía para exponer la fase TEST

## Verificación realizada en este equipo — 19 de octubre de 2026

- Suite completa: **41 passed**; incluye las seis pruebas de exposición.
- Selenium en Microsoft Edge: recorrido completado con éxito y capturas guardadas.
- `pip check`: sin dependencias rotas.
- Flake8: sin errores en los archivos Python nuevos y en la fixture modificada.
- Postman de escritorio **12.32.4** instalado; colección con JSON y scripts
  sintácticamente válidos. Importar la colección en su interfaz siguiendo los
  pasos de esta guía.

## Antes de pasar al frente

Usar este repositorio en `C:\AeroGuard`. Se necesita Python 3.11 o 3.12,
Microsoft Edge y Postman de escritorio. En este equipo, `venv` usa Python
3.12.14 disponible con las herramientas locales de Codex. No hace falta
activar el entorno si se usan los comandos completos que aparecen abajo.
Git y Docker Desktop ya están instalados; Docker puede estar cerrado.

La primera preparación instala las dependencias y descarga el controlador
de Edge. Ejecutar Selenium antes de la clase y conservar el caché `.wdm`.
El mapa usa bibliotecas y teselas de Internet: comprobar la conexión antes
de exponer. Las pruebas de API trabajan con SQLite temporal y no necesitan
PostgreSQL, RabbitMQ ni servicios de IA externos.

La interfaz existente está en **modo demo con datos simulados**. El recorrido
Selenium verifica ese flujo de interfaz; PyTest y Postman prueban la API real.

| Dónde se inicia sesión | Usuario | Contraseña local |
| --- | --- | --- |
| Interfaz demo / Selenium | admin | `Admin123!` |
| API / Postman / SQLite inicial | admin | `Admin@12345` |

Estas credenciales pertenecen al prototipo local. La API conserva su semilla
en `tmp/expo/aeroguard.db`; las pruebas usan otra base temporal, independiente.

## Los tres comandos, en este orden

Abrir PowerShell en `C:\AeroGuard`.

**1. Iniciar backend y frontend**

```powershell
.\INICIAR_EXPO_LUNES.bat
```

También se puede hacer doble clic en ese archivo antes de la exposición.
Esperar el mensaje de disponibilidad y pulsar una tecla para cerrar la
ventana. Los dos procesos permanecen en segundo plano. Ejecutarlo otra vez
reutiliza los servicios si ya están disponibles.

- Interfaz: <http://127.0.0.1:3000>
- API interactiva: <http://127.0.0.1:8000/docs>
- Salud: <http://127.0.0.1:8000/health>
- Logs: `tmp/expo/backend.log` y `tmp/expo/frontend.log`.

**2. Mostrar las seis pruebas PyTest**

```powershell
.\venv\Scripts\python.exe -m pytest backend\tests\test_exposicion_lunes.py -v
```

La suite verifica salud; login y JWT con rechazo de clave incorrecta;
procesamiento de JPEG sintético; rechazo de texto; PDF con huella; y Excel
que se abre como libro válido. El resultado esperado es **6 passed**.
No se omiten pruebas ni se fuerzan resultados verdes.

**3. Ejecutar el recorrido visible en Edge**

```powershell
.\venv\Scripts\python.exe tests\demo_selenium_lunes.py
```

Edge abre una sesión temporal, escribe las credenciales, muestra el mapa,
visita Sensores y Reportes con pausas de dos segundos y se cierra. Comprueba
que el mapa se renderiza y que la vista de sensores carga datos.
Guarda `docs/evidencia_selenium.png` y `docs/evidencia_selenium_mapa.png`.
Solo al completar el recorrido imprime:

```text
✅ PRUEBA E2E SELENIUM COMPLETADA CON ÉXITO
```

Un fallo devuelve error y, si el navegador llegó a abrirse, deja una captura
en `docs/evidencia_selenium_error.png`.

## Postman en la exposición

1. Abrir **Postman de escritorio** e importar `docs/AeroGuard_Postman_Collection.json`.
2. En la configuración de archivos, usar `C:\AeroGuard` como directorio de
   trabajo. En **03 — Analizar imagen**, confirmar en Body → form-data que
   `file` apunta a `docs/assets/drone_demo.jpg`; si Postman no resuelve la
   variable de ruta, seleccionar ese archivo mediante el selector.
3. Enviar las peticiones en orden: Salud, Login, Analizar imagen, PDF y Excel.
   Login guarda el JWT en la variable de colección `access_token`.
4. Mostrar los resultados de **Tests / Test Results** y usar **Send and
   Download** si se quiere guardar el PDF o el Excel.

Cada petición hereda pruebas de código 200 y tiempo de respuesta menor de
1000 ms. Hay comprobaciones adicionales de JWT, detección y tipo de archivo.
El tiempo se mide realmente: con carga alta del equipo puede fallar el
umbral; se explica el resultado en lugar de ocultarlo. Al volver a importar
la colección, ejecutar Login otra vez para obtener un token vigente.

## Qué decir de las siete herramientas

| Herramienta | Explicación breve | Qué mostramos |
| --- | --- | --- |
| **PyTest** | Ejecuta pruebas Python y muestra qué condiciones pasan o fallan. | Seis pruebas de integración contra FastAPI y SQLite temporal. |
| **Postman** | Envía peticiones HTTP y ejecuta comprobaciones sobre las respuestas. | Login JWT, salud, imagen y exportaciones con scripts `pm.test`. |
| **Selenium** | Automatiza un navegador para comprobar el flujo que ve el usuario. | Edge visible: login demo, mapa, sensores, reportes y capturas. |
| **Cucumber / Gherkin** | Gherkin describe ejemplos Dado/Cuando/Entonces; Cucumber necesita pasos programados para ejecutarlos. | Lectura de `backend/tests/features/aeroguard_bdd.feature` en español. Es especificación BDD, no una suite Cucumber ejecutada. |
| **JUnit** | Framework de pruebas del ecosistema Java. | Se explica; AeroGuard no tiene un backend Java ni una suite JUnit. |
| **Jasmine** | Framework para pruebas de código JavaScript. | Se explica; no se ha creado una suite Jasmine para esta exposición. |
| **Appium** | Automatiza aplicaciones móviles mediante controladores de plataforma. | Se explica; el proyecto presentado es web y no incluye una app móvil. |

Las cuatro demostraciones son **PyTest, Postman, Selenium y los escenarios
BDD escritos en Gherkin**. La automatización ejecutada corresponde a las
tres primeras; leer un `.feature` no equivale a ejecutar Cucumber.

## Alcance de la evidencia

- La imagen sintética es cielo con un recuadro oscuro. Valida el endpoint
  y su contrato, no demuestra precisión de reconocimiento de drones reales.
- El modo local usa el motor heurístico OpenCV/Pillow del proyecto. La
  respuesta identifica el motor ejecutado; no se presenta como YOLO entrenado.
- Los reportes existentes usan datos de demostración. `X-Report-SHA256`
  es una huella de la serialización de esos datos. No es una firma digital
  y no debe compararse con el hash de los bytes del PDF.
- El escenario de sonido en geocerca es un criterio BDD escrito. No está
  cubierto por estas seis pruebas ni por el recorrido Selenium.

## Repetir la preparación en otro equipo

Instalar Python 3.12, Git, Edge y Postman. Clonar el repositorio y abrirlo en
el editor. Desde la raíz:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r backend\requirements-expo.txt
Copy-Item .env.example .env
```

Generar una `SECRET_KEY` propia en `.env`. El iniciador fuerza SQLite para
sus procesos locales aunque la plantilla mencione PostgreSQL. No sobrescribir
un `.env` que ya tenga configuración propia. `venv`, `.env`, bases, cachés
y logs no se suben a Git. Conservar la imagen de prueba en `docs/assets`.

Para comprobar toda la suite, ejecutar `.\venv\Scripts\python.exe -m pytest -v`.
Si el inicio informa que un puerto está ocupado, revisar qué aplicación usa
3000 u 8000 y cerrarla desde su propia interfaz. El iniciador no termina
procesos ajenos. Los servidores locales se cierran al reiniciar Windows;
sus PID se muestran al iniciarlos y pueden cerrarse desde el Administrador
de tareas al terminar la demostración.
