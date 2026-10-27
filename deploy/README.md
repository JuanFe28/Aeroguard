# Deploy privado de la candidata académica

Este paquete prepara **una instalación nueva** de `1.2.0-rc.1` en un servidor Linux `x86_64`. Usa las imágenes publicadas por digest: no reconstruye ni sustituye la candidata. Sirve para un servidor físico o una VM; se necesita un solo destino.

## Acceso y alcance

El único puerto publicado es `127.0.0.1:8080`. Se accede desde un equipo autorizado mediante un túnel SSH sobre Tailscale. La base de datos, RabbitMQ, el backend, el worker y el simulador no publican puertos del host. La red de datos es interna; las integraciones salientes como SMTP/n8n requieren una revisión posterior. No hace falta dominio, abrir puertos del router ni activar Tailscale Funnel.

Las claves SSH se quedan en el equipo que ya tiene acceso. Este repositorio no contiene direcciones del servidor personal ni claves privadas. Los servicios usan volúmenes propios y límites de recursos. El backend utiliza raíz de solo lectura, capacidades reducidas y temporales limitados. Estas medidas reducen exposición; no certifican seguridad absoluta del equipo anfitrión.

## 1. Revisar el servidor antes de cambiarlo

Si el destino Ubuntu todavía no tiene Docker, seguir primero la [preparación de Docker rootless](ubuntu-rootless.md). Es un procedimiento por etapas, pendiente de validar en el destino real, que propone una cuenta exclusiva y conserva los servicios personales existentes.

Entra utilizando la conexión SSH que ya tienes configurada. Conserva la validación de la huella del servidor. Revisa arquitectura, RAM disponible, espacio, Docker y servicios existentes con:

```sh
sh deploy/preflight.sh
```

El script solo consulta información. Docker debe estar instalado y ser accesible para el usuario autorizado. Se exige Engine 28 o superior por la corrección de aislamiento de puertos publicados en localhost. Consulta la [documentación de puertos de Docker](https://docs.docker.com/engine/network/port-publishing/). No cambies permisos de `docker.sock`, pertenencias a grupos, reglas de firewall ni servicios existentes para superar una comprobación fallida.

Como punto de partida para un ensayo pequeño, prever 4 GB de RAM y 2 CPU disponibles; con otros servicios conviene mayor margen. Es una estimación que debe contrastarse con el uso real. Comprobar copias de seguridad y espacio antes de instalar. Si el puerto 8080 ya está ocupado, utilizar otro puerto local tanto en `--port` como en `--url`.

## 2. Preparar una instalación nueva

Conservar el proyecto en una carpeta propia, fuera de carpetas compartidas de archivos. Desde la raíz del repositorio, usando Python 3:

```sh
python3 scripts/prepare_deploy.py
python3 scripts/check_deploy_layout.py
```

Se crea `deploy/.env` con secretos aleatorios y permisos `0600` en Linux. El archivo queda fuera de Git y el script se niega a sobrescribirlo. La contraseña inicial está en `BOOTSTRAP_ADMIN_PASSWORD`: consultarla únicamente en el equipo autorizado y conservar un respaldo privado. No pegar el archivo en chats, issues ni artefactos de CI.

`COMPOSE_PROJECT_NAME` determina los volúmenes. No reutilizar el nombre de una instalación diferente ni conectar volúmenes anteriores sin un procedimiento de migración y backup. PostgreSQL/PostGIS y RabbitMQ también se fijan por digest. RabbitMQ 4.3.6 se usa con un volumen nuevo, no como actualización directa de un broker 3.13 existente.

## 3. Levantar y comprobar

Solo después de revisar el servidor y aceptar la instalación:

```sh
docker compose --env-file deploy/.env -f deploy/compose.yml pull
docker compose --env-file deploy/.env -f deploy/compose.yml up -d --wait --wait-timeout 180
python3 scripts/check_deploy.py --output backups/deploy-check-inicial.json
```

En la primera instalación, antes de abrir sesiones de trabajo, se puede verificar también el administrador:

```sh
python3 scripts/check_deploy.py --check-bootstrap-login --output backups/deploy-check-login.json
```

Este último comando cierra las sesiones del administrador al terminar. La comprobación normal no inicia sesiones, no sigue redirecciones y no usa proxies del entorno. Usar nombres nuevos para las evidencias. La prueba de login requiere que la contraseña inicial siga vigente.

Los perfiles `ai` y `demo` son opcionales. Exigen tokens de usuarios dedicados y sensores registrados; no se activan por defecto. El backend ya puede procesar imágenes mediante su endpoint autenticado. No atribuir reconocimiento validado a las heurísticas.

## 4. Acceder por el túnel existente

Desde tu portátil autorizado, abrir un túnel con la misma clave y usuario de tu conexión SSH habitual, agregando:

```text
-o ExitOnForwardFailure=yes -L 127.0.0.1:8080:127.0.0.1:8080 -N
```

La conexión debe dirigirse a tu servidor por Tailscale. Mientras el túnel esté abierto, visitar `http://localhost:8080`. No desactivar la comprobación de huellas SSH. Cerrar el túnel cierra ese acceso local; no publica AeroGuard en Internet.

## Detener y recuperar

```sh
docker compose --env-file deploy/.env -f deploy/compose.yml stop
```

Esto conserva los volúmenes. Evitar `down -v`, limpiezas de volúmenes y cambios de proyecto que oculten datos. Para backups se puede usar `scripts/database_backup.py`, pasando los nombres de contenedor devueltos por `docker compose ... ps`. Conservar tanto PostgreSQL como los reportes originales y la configuración privada.

El manifiesto `release.json` permite comprobar las imágenes exactas. Para regresar a una versión anterior, conservar su manifiesto y evaluar la compatibilidad del esquema antes de arrancarla. No restaurar una base sobre otra activa sin una recuperación ensayada.

## Criterio de cierre de Deploy

La validación local y el workflow `deploy-check.yml` son ensayos. **DEPLOY-02 sigue pendiente** hasta verificar en el servidor real: recursos, imágenes, salud, acceso por túnel, bloqueo de accesos anónimos, persistencia tras reinicio de contenedores y recuperación. No se ha instalado este paquete en el servidor de casa durante la preparación.
