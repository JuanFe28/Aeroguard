# Preparación de Ubuntu con Docker rootless

La preparación rootless se completó y verificó en el servidor real el 28 de octubre de 2026. Se conservaron los servicios existentes y se bloquearon las unidades globales nuevas antes de instalar los cinco paquetes previstos. La cuenta exclusiva no tiene sudo y dispone de límites agregados de 4 GiB de RAM, 1 GiB de swap, dos CPU equivalentes y 768 tareas. Un contenedor temporal confirmó la aplicación de límites propios de memoria, swap, CPU y procesos. [Evidencia del servidor](evidence/2026-10-28-server.json).

Los pasos siguientes conservan el historial del procedimiento. No deben repetirse sobre la instalación existente. El ensayo de CI por sí solo no reemplaza las comprobaciones del destino. No ejecutar directamente la instalación general de Docker: sus paquetes pueden arrancar un motor global automáticamente.

El destino revisado mediante capturas del operador es Ubuntu 24.04 LTS, `x86_64`, con capacidad suficiente para un ensayo pequeño. Docker aún no está disponible. UFW figura activo con bloqueo de entrada por defecto y permisos específicos; SSH, Samba y Tailscale ya prestan servicios. Las capturas no comprueban las reglas completas de Tailscale, los permisos de la tailnet ni el router. Conservar esta configuración y el acceso SSH existente.

## Primera etapa: comprobar requisitos sin instalar

Desde la sesión SSH que ya funciona, ejecutar:

```sh
stat -fc %T /sys/fs/cgroup
getent passwd aeroguard
systemctl is-active docker.service docker.socket containerd.service
sudo apt-get --simulate --no-remove install --no-install-recommends ca-certificates curl uidmap dbus-user-session slirp4netns systemd-container
```

La primera salida debe indicar `cgroup2fs` para la estrategia propuesta. Una cuenta `aeroguard` preexistente requiere revisar su uso antes de reutilizarla; no modificarla automáticamente. Las unidades del sistema se consultan para detectar instalaciones previas. La simulación de Apt no instala ni elimina paquetes; no añadir Docker a esa orden hasta revisar el origen y el plan de paquetes. Si falla, conservar el error y revisar la causa.

El 27/10/2026 el operador confirmó `cgroup2fs`, ausencia de la cuenta y tres unidades inactivas. Instaló los cinco paquetes nuevos de la simulación: `libslirp0`, `libsubid4`, `slirp4netns`, `systemd-container` y `uidmap`. No se eliminaron ni actualizaron paquetes; la salida no solicitó reinicios de servicios. Los 16 paquetes pendientes de actualización requieren una revisión separada, incluyendo cuáles corresponden a seguridad.

## Segunda etapa: repositorio oficial y simulación del motor

El siguiente bloque corresponde exclusivamente a Ubuntu 24.04 `amd64`, como el destino revisado. Añade la clave pública descargada por HTTPS del sitio oficial y la fuente de Apt; actualiza el catálogo y **solo simula** instalar Docker. No ejecuta scripts descargados. Se detiene si detecta una fuente Docker o los archivos de destino existentes, para evitar sobrescribir configuraciones previas.

```sh
bash <<'AEROGUARD'
set -euo pipefail
if [ -e /etc/apt/keyrings/docker.asc ] || [ -e /etc/apt/sources.list.d/docker.sources ] || grep -RqsF 'download.docker.com' /etc/apt/sources.list /etc/apt/sources.list.d; then
  printf 'Ya existe configuración de Docker. Revisarla antes de continuar.\n'
  exit 1
fi
aeroguard_key_file=$(mktemp)
trap 'rm -f -- "$aeroguard_key_file"' EXIT
curl --proto '=https' --tlsv1.2 -fsS https://download.docker.com/linux/ubuntu/gpg -o "$aeroguard_key_file"
sudo install -m 0755 -d /etc/apt/keyrings
sudo install -m 0644 "$aeroguard_key_file" /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<'DOCKER_SOURCE'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
DOCKER_SOURCE
sudo apt-get update
sudo apt-get --simulate --no-remove install --no-install-recommends docker-ce docker-ce-cli containerd.io docker-ce-rootless-extras docker-compose-plugin
AEROGUARD
```

Revisar la salida antes de ejecutar una instalación real del motor. Si algún paso falla, no borrar archivos ni repetir el bloque automáticamente: inspeccionar lo que sí llegó a crearse. No quitar `--simulate` todavía; falta impedir el arranque de las nuevas unidades globales y preparar la cuenta de rootless.

El operador confirmó esta etapa el 27/10/2026: se descargó el catálogo firmado del repositorio oficial y terminó la simulación, sin instalar el motor. El plan proponía cinco paquetes nuevos, cero eliminaciones y cero actualizaciones: Docker CE/CLI y rootless extras 29.9.2, containerd.io 2.4.2 y Compose 5.6.1. Esas son las versiones propuestas entonces, no una instalación comprobada; volver a revisar el plan al retomar. Permanecían 16 paquetes sin actualizar. No repetir el bloque de creación del repositorio, porque los archivos de la fuente y su clave ya existen.

## Etapas posteriores realizadas y verificadas el 28 de octubre

1. Revisar la simulación, paquetes existentes y repositorios. Preparar el repositorio oficial de Docker y comprobar su clave. Instalar únicamente los paquetes necesarios, impidiendo el arranque automático de las nuevas unidades Docker del sistema antes de instalar el motor. No deshabilitar servicios previos de otro proyecto.
2. Crear una cuenta exclusiva sin contraseña de acceso remoto, sin sudo ni grupos de archivos compartidos, con carpeta privada. No dar acceso al socket de Docker del sistema a la cuenta personal. Conservar las claves SSH en el portátil autorizado.
3. Instalar rootless con una sesión de usuario de systemd mediante `machinectl`, siguiendo la documentación. Ubuntu 24.04 restringe los espacios de nombres de usuario; utilizar los paquetes oficiales y comprobar su perfil de RootlessKit. No desactivar AppArmor ni las restricciones globales para resolver errores.
4. Verificar `rootless`, driver de cgroups `systemd`, versión 2 y delegación efectiva de CPU, memoria y procesos. Aplicar la configuración necesaria únicamente a la nueva cuenta, no a todas las sesiones de usuario. Establecer también límites agregados para proteger los servicios personales del anfitrión. Comprobar los límites con un contenedor antes de desplegar la aplicación.
5. Guardar el repositorio y los secretos bajo la cuenta exclusiva. Continuar con la validación de `compose.yml`, las imágenes fijadas y la instalación nueva descrita en [README.md](README.md).
6. Comprobar acceso por túnel, escucha solo en loopback, salud, autenticación, persistencia y recuperación. Comparar UFW, SSH, Tailscale y acceso a archivos con el estado anterior. No publicar la API de Docker por TCP.

Los límites de recursos del modo rootless requieren cgroup v2 y systemd; su presencia en Compose no demuestra que el host los aplique. En este destino se comprobaron los valores agregados y los límites dentro de un contenedor. Docker rootless reduce privilegios del motor y de los contenedores; no certifica la seguridad completa del servidor. El cierre del stack básico y sus límites se documenta en [la guía de Deploy](README.md#criterio-de-cierre-de-deploy).

## Fuentes oficiales

- [Funcionamiento y requisitos de rootless](https://docs.docker.com/engine/security/rootless/)
- [Sesiones de systemd y particularidades de Ubuntu](https://docs.docker.com/engine/security/rootless/troubleshoot/)
- [Límites de recursos y delegación de cgroups](https://docs.docker.com/engine/security/rootless/tips/#limiting-resources)
- [Instalación en Ubuntu y arranque automático del servicio](https://docs.docker.com/engine/install/ubuntu/)
