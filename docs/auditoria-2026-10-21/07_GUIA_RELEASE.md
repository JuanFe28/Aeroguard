# Guía de verificación, demo y operación académica

Alcance: laboratorio local con datos sintéticos. No sustituye un manual de operación con sensores reales. Usar una carpeta nueva para cada ejecución de evidencias; el verificador rechaza carpetas que ya contienen archivos.

## Instalación y verificación del código

Desde la raíz del clon, con Python 3.11 y Node disponibles:

```powershell
cd D:\aeroguard
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-expo.txt
.\.venv\Scripts\python.exe scripts/release_checks.py --output tmp/release-repro-01
```

Para comprobar avisos conocidos, instalar `pip-audit==2.9.0` en ese entorno y añadir `--audit-dependencies`. Requiere Internet y devuelve fallo si encuentra vulnerabilidades. Sin ese parámetro, un resultado verde solo cubre sintaxis, pytest, carga WS y el umbral SAST declarado; **no autoriza Release**.

Windows puede requerir acceso de lectura al registro para que OpenPyXL resuelva los MIME. En esta auditoría se ejecutó con la autorización correspondiente. Las pruebas usan SQLite temporal, no la BD de la demo. El verificador desactiva n8n y YOLO y coloca sus archivos temporales dentro del repositorio. No envía correos ni mensajes a terceros.

## Demostración para el usuario

```powershell
.\.venv\Scripts\python.exe scripts/expo_local.py
```

Este lanzador crea procesos locales sin ventana y los deja activos: frontend `http://127.0.0.1:3000`, API `http://127.0.0.1:8000/docs`. Registra sus PID y logs en la salida/`tmp/expo`; solo detener procesos identificados como creados por esa ejecución. No usar el BAT eliminado como requisito de esta guía.

1. Abrir frontend y comprobar el rótulo de demo. Entrar con `admin / Admin123!` (o las credenciales demo de la pantalla).
2. Mostrar mapa, alertas, sensores y altimetría explicando que son datos simulados y que las zonas/umbrales de ejemplo no son cartografía normativa.
3. Mostrar reportes y sus límites. La prueba de archivos reales se hace contra API, no mediante los mocks del navegador.
4. En Swagger, usar la cuenta inicial de laboratorio `admin / Admin@12345` o un usuario creado para el ensayo. Es distinta de la cuenta de la demo visual.
5. Consultar salud, login, análisis de una imagen de prueba y exportaciones. Identificar heurística y origen sintético, sin afirmar un reconocimiento validado.

Roles: administrador configura y gestiona usuarios; operador consulta detecciones y gestiona alertas; analista consulta/exporta reportes. La guía histórica detalla más pantallas, pero algunas aún operan con mocks. Recuperación de contraseña y envío SMTP requieren configuración y pruebas adicionales.

Recorrido automatizado sin ventana:

```powershell
.\.venv\Scripts\python.exe tests/demo_selenium_lunes.py --headless --evidence-dir tmp/demo-evidence-01
```

Puede descargar un controlador de Edge. Usa perfil temporal, verifica login/mapa/sensores/reportes y cierra el navegador. No comprueba todas las acciones ni la integración completa con la API. Las teselas, fuentes y Leaflet dependen de Internet; comprobar conectividad antes de exponer y conservar capturas para explicar una caída de red, sin presentarlas como sesión en vivo.

## Desarrollo

Backend: `backend/app/main.py`; crear cambios pequeños en routers/servicios, con regresión de comportamiento observable cuando se corrige un defecto. Frontend: `frontend/src/main.js`, vistas/viewmodels/servicios. Revisar el contrato OpenAPI actual antes de conectar una pantalla: no asumir que todos los métodos del cliente existen en el servidor.

`npm run lint` hoy valida sintaxis. Para lint real se usan las tareas `lint:py`/`lint:js` y sus dependencias; no se declaró pasada una revisión de estilo completa. El informe de cobertura mide líneas del backend. Cada ampliación a BD, scheduler o sensores debe incluir criterios de aceptación y origen de datos.

## Contenedores — instrucciones preparadas, sin ejecución verificada

Ejecutar en máquina o VM de laboratorio aislada, con Docker iniciado y sin un stack que use los mismos nombres. Compose fija nombres de contenedores, redes y volúmenes; cambiar solo `-p` no garantiza aislamiento.

```powershell
docker compose config --quiet
docker build -f backend/Dockerfile --target test -t aeroguard/backend:test .
docker compose build
```

Después de revisar configuración y secretos del ensayo, iniciar el stack y comprobar logs, salud, login, BD efectiva y eventos. No basta que `/health` devuelva 200: actualmente no verifica dependencias. Confirmar acceso desde el cliente correcto: el frontend todavía referencia localhost y modo demo por defecto. No usarlo como despliegue remoto listo.

El simulador ahora necesita `SIMULATOR_TOKEN` con permiso `detections:write`; no introducirlo en Git. El callback y disparo de n8n también necesitan Bearer. Configurar una identidad de servicio y el destino de webhook en la red elegida antes de ensayar; el workflow exportado no está listo para usarse sin esa adaptación. No activar los nodos de mensajería durante las pruebas sin autorización específica.

La imagen PostgreSQL actual no incluye PostGIS. El sistema utiliza ray-casting; no afirmar que `ST_Contains` se ejecuta. El consumidor IA tiene una actualización de BD pendiente. Si esas capacidades son requisito docente, su prueba sigue abierta.

## Respaldo y restauración — procedimiento por ensayar

Definir RPO/RTO con el responsable; no se han medido. Respaldar BD, archivos de reportes, versión/digests y configuración de forma cifrada y con acceso restringido. Excluir tokens y claves de los paquetes académicos.

Ejemplo de dump PostgreSQL de una instalación de laboratorio ya identificada:

```powershell
docker exec aeroguard-postgres pg_dump -U aeroguard -Fc -f /tmp/aeroguard-lab.dump aeroguard
docker cp aeroguard-postgres:/tmp/aeroguard-lab.dump tmp/aeroguard-lab.dump
Get-FileHash tmp/aeroguard-lab.dump -Algorithm SHA256
```

Restaurar primero en **otra base o instancia desechable**, con la misma versión compatible. Usar `createdb` y `pg_restore` con destino explícito nuevo; no incluir `--clean` ni sobrescribir la base de trabajo. Verificar recuentos, usuarios, zonas, detecciones, relaciones y hashes; guardar duración y resultados. Para SQLite de demo, detener el proceso antes de copiar o utilizar el backup consistente del motor; no copiar una BD en escritura como evidencia fiable. Guardar también los reportes y probar su recuperación, pues las descargas por ID aún no leen el archivo persistido.

## Reversión

Antes de actualizar: inventario de versión/configuración, backup restaurable y digests anteriores. Activar reversión si no hay readiness/BD, fallan login o permisos, o se pierde persistencia. Detener solo el stack objetivo, volver a imágenes por digest y comprobar smoke. Si hubo cambio de esquema, validar compatibilidad o restaurar a instancia nueva; `create_all` no es un sistema de migraciones reversible. No ejecutar borrado de volúmenes (`down -v`) como mecanismo de rollback. Registrar decisión, recuperación y diferencias de datos.

Este procedimiento es una recomendación preparada. Ni la restauración ni la reversión se han ensayado en esta sesión.
