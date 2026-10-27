# Preparación de Ubuntu con Docker rootless

Este procedimiento está en preparación. El ensayo de `compose.yml` aprobado en CI no valida todavía una instalación rootless en el servidor real. No ejecutar directamente la instalación general de Docker: en Ubuntu sus paquetes pueden arrancar un motor del sistema automáticamente.

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

## Etapas posteriores, pendientes de ejecutar y comprobar

1. Revisar la simulación, paquetes existentes y repositorios. Preparar el repositorio oficial de Docker y comprobar su clave. Instalar únicamente los paquetes necesarios, impidiendo el arranque automático de las nuevas unidades Docker del sistema antes de instalar el motor. No deshabilitar servicios previos de otro proyecto.
2. Crear una cuenta exclusiva sin contraseña de acceso remoto, sin sudo ni grupos de archivos compartidos, con carpeta privada. No dar acceso al socket de Docker del sistema a la cuenta personal. Conservar las claves SSH en el portátil autorizado.
3. Instalar rootless con una sesión de usuario de systemd mediante `machinectl`, siguiendo la documentación. Ubuntu 24.04 restringe los espacios de nombres de usuario; utilizar los paquetes oficiales y comprobar su perfil de RootlessKit. No desactivar AppArmor ni las restricciones globales para resolver errores.
4. Verificar `rootless`, driver de cgroups `systemd`, versión 2 y delegación efectiva de CPU, memoria y procesos. Aplicar la configuración necesaria únicamente a la nueva cuenta, no a todas las sesiones de usuario. Establecer también límites agregados para proteger los servicios personales del anfitrión. Comprobar los límites con un contenedor antes de desplegar la aplicación.
5. Guardar el repositorio y los secretos bajo la cuenta exclusiva. Continuar con la validación de `compose.yml`, las imágenes fijadas y la instalación nueva descrita en [README.md](README.md).
6. Comprobar acceso por túnel, escucha solo en loopback, salud, autenticación, persistencia y recuperación. Comparar UFW, SSH, Tailscale y acceso a archivos con el estado anterior. No publicar la API de Docker por TCP.

Los límites de recursos del modo rootless requieren cgroup v2 y systemd; su presencia en Compose no demuestra que el host los aplique. Docker rootless reduce privilegios del motor y de los contenedores; no certifica la seguridad completa del servidor. DEPLOY-02 continúa pendiente.

## Fuentes oficiales

- [Funcionamiento y requisitos de rootless](https://docs.docker.com/engine/security/rootless/)
- [Sesiones de systemd y particularidades de Ubuntu](https://docs.docker.com/engine/security/rootless/troubleshoot/)
- [Límites de recursos y delegación de cgroups](https://docs.docker.com/engine/security/rootless/tips/#limiting-resources)
- [Instalación en Ubuntu y arranque automático del servicio](https://docs.docker.com/engine/install/ubuntu/)
