# Entrega 1.2.0-rc.2: de GitHub al servidor

Actualizado: 11-11-2026. Es la guía vigente para llevar **1.2.0-rc.2** al servidor privado. Reemplaza, para esta versión, los pasos 2 y 5 de [COMANDOS_SERVIDOR_CASA.txt](COMANDOS_SERVIDOR_CASA.txt), que se conserva como referencia del 29-10-2026.

**Quién hace qué:** la parte A la puede hacer cualquier integrante con permisos de escritura en `JuanFe28/Aeroguard`. La parte B solo la hace quien administra el servidor, desde el portátil con la identidad SSH autorizada.

## Qué cambia respecto a rc.1 (lo que hoy corre en el servidor)

- Correcciones de QA del 29-10 (configuración, sensores, usuarios, mapas, trayectorias, reportes programados, validaciones UUID).
- Mapas con fondo en Docker: la CSP de Nginx ya permite las teselas de OpenStreetMap.
- Perfil de usuario rediseñado, con cambio de contraseña y cierre de sesión.
- **Base de datos:** no hay tablas ni columnas nuevas. Volver a rc.1 no requiere migrar ni restaurar la base.
- Módulo de minería de datos: no se despliega en el servidor (solo vive en el repositorio).

## Parte A: publicar las imágenes (GitHub)

1. **Fusionar a `main`.** Revisa el PR de `chore/rc2-preparacion` hacia `main`, espera los checks en verde y fusiónalo.
2. **Publicar.** En *Actions → Release de AeroGuard en GHCR → Run workflow*, elige la rama `main` y la versión `1.2.0-rc.2`. Debe terminar en verde (quality + 4 publicaciones).
3. **Copiar los resultados.** En el resumen de la ejecución aparecen 4 líneas *Imagen publicada y comprobada* con la forma `ghcr.io/juanfe28/aeroguard-<componente>:1.2.0-rc.2@sha256:...`. Copia también el SHA completo del commit que se publicó y la URL de la ejecución.
4. **Fijar los digests** en un clon actualizado de `main`, en una rama nueva:

   ```powershell
   git switch main; git pull --ff-only; git switch -c chore/fijar-rc2
   python scripts/set_release_digests.py --version 1.2.0-rc.2 --commit <SHA completo> `
     --evidence <URL de la ejecución> <línea backend> <línea frontend> <línea ai-service> <línea simulator>
   git diff deploy/        # solo deben cambiar compose.yml y release.json
   git commit -am "chore(release): fijar imágenes publicadas de 1.2.0-rc.2"
   git push -u origin chore/fijar-rc2
   ```

   Abre el PR, espera los checks y fusiónalo. El script valida el formato, la versión y que estén los cuatro componentes, y actualiza los dos archivos a la vez para que no queden desalineados.
5. **Etiqueta y prerelease.** Crea la etiqueta `v1.2.0-rc.2` sobre el **commit que construyó las imágenes** (el del paso 3) y la prerelease en GitHub con las notas del `CHANGELOG.md`. No reutilices ni muevas la etiqueta `v1.2.0-rc.1`.

## Parte B: actualizar el servidor (compañero)

Mismas reglas del TXT del 29-10: usuario `aeroguard`, Docker rootless, sin `down -v`, sin regenerar `deploy/.env` y sin pegar secretos en chats ni en GitHub. Si un bloque falla, **no sigas con el siguiente**.

1. **Diagnóstico.** Ejecuta el paso 1 de [COMANDOS_SERVIDOR_CASA.txt](COMANDOS_SERVIDOR_CASA.txt) y anota el commit actual (`git log -1`) para poder volver.
2. **Respaldo y actualización.** En PowerShell del portátil, con `$aeroDestino` definido como en el TXT:

   ```powershell
   @'
   set -eu
   test "$(id -un)" = aeroguard || { echo "Usuario inesperado; detener"; exit 1; }
   export XDG_RUNTIME_DIR="/run/user/$(id -u)"
   export DOCKER_HOST="unix://$XDG_RUNTIME_DIR/docker.sock"
   cd /home/aeroguard/AeroGuard
   test -z "$(git status --porcelain --untracked-files=no)" || { echo "Cambios locales en archivos versionados; conservarlos y revisar"; exit 1; }
   anterior=$(git rev-parse HEAD); echo "Commit anterior: $anterior"
   git fetch origin main
   git show origin/main:deploy/release.json | grep -q '"version": "1.2.0-rc.2"' || { echo "main aun no fija rc.2; terminar la parte A"; exit 1; }
   envfile=deploy/.env
   stamp=$(date -u +%Y%m%dT%H%M%SZ)
   db=$(docker compose --env-file "$envfile" -f deploy/compose.yml ps -q postgres)
   api=$(docker compose --env-file "$envfile" -f deploy/compose.yml ps -q backend)
   test -n "$db" && test -n "$api"
   umask 077
   python3 scripts/database_backup.py --container "$db" --reports-container "$api" --output "backups/pre-rc2-$stamp.dump"
   git checkout --detach origin/main
   python3 scripts/check_deploy_layout.py --env-file "$envfile"
   docker compose --env-file "$envfile" -f deploy/compose.yml pull
   docker compose --env-file "$envfile" -f deploy/compose.yml up -d --wait --wait-timeout 180
   python3 scripts/check_deploy.py --env-file "$envfile" --output "backups/rc2-$stamp.json"
   docker compose --env-file "$envfile" -f deploy/compose.yml ps --format 'table {{.Name}}\t{{.Image}}\t{{.Status}}'
   '@ | ssh -T $aeroDestino 'tr -d "\r" | bash -s'
   if ($LASTEXITCODE -ne 0) { throw "Actualizacion no completada: revisar la salida y, si hace falta, volver atras" }
   ```

   `check_deploy_layout.py` confirma que las imágenes de Compose coinciden con `release.json` y que el puerto sigue privado. `check_deploy.py` comprueba la salud del despliegue y guarda el resultado en `backups/` (privado, fuera de Git). El login se revisa a mano en el paso 3.
3. **Revisión manual.** Abre el túnel del paso 4 del TXT, entra a `http://127.0.0.1:18080` con el admin del `.env` privado y revisa: mapa con fondo, perfil nuevo, zonas, sensores, alertas y un reporte. Guarda una captura sin datos sensibles.
4. **Volver atrás si algo falla.** Como el esquema no cambió, basta con regresar al commit anterior y levantar las imágenes de rc.1:

   ```bash
   cd /home/aeroguard/AeroGuard
   git checkout --detach <commit anterior anotado en el paso 2>
   docker compose --env-file deploy/.env -f deploy/compose.yml up -d --wait --wait-timeout 180
   ```

   Restaura el respaldo `backups/pre-rc2-*.dump` solo si se comprueba un daño en los datos, y siguiendo el manual de operación.

## Cierre

- Avisa en el grupo el commit desplegado, la hora y el resultado de `check_deploy.py` (sin secretos).
- Trello: DEPLOY-02 pasa a rc.2 con esta evidencia. Monitor, SMTP/n8n, sensores físicos y validación independiente de IA siguen pendientes; esta actualización no los completa.
