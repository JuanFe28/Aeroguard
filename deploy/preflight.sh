#!/bin/sh
# Inspección de lectura. No instala paquetes, cambia firewall ni solicita claves.
set -eu
printf 'Arquitectura: '
uname -m
printf '\nMemoria disponible:\n'
free -h
printf '\nEspacio disponible en la carpeta de usuario:\n'
df -h "$HOME"
printf '\nPuerto local 8080 (una fila significa que está ocupado):\n'
ss -ltn '( sport = :8080 )'
if ! command -v docker >/dev/null 2>&1; then
  printf '\nDocker no está instalado. Revisar instalación con el administrador antes de continuar.\n'
  exit 1
fi
printf '\nVersiones de Docker:\n'
engine_version=$(timeout 10 docker version --format '{{.Server.Version}}')
printf 'Engine: %s\n' "$engine_version"
engine_major=${engine_version%%.*}
case "$engine_major" in ''|*[!0-9]*) printf 'No se pudo verificar la versión del motor.\n'; exit 1;; esac
if [ "$engine_major" -lt 28 ]; then
  printf 'Se requiere Docker Engine 28 o superior para este despliegue privado.\n'
  exit 1
fi
docker compose version
printf '\nOpciones de seguridad del motor:\n'
timeout 10 docker info --format '{{json .SecurityOptions}}'
printf '\nServicios Docker existentes; conservar su configuración:\n'
docker ps --format 'table {{.Names}}\t{{.Ports}}'
printf '\nInspección completada. No se ha desplegado ni modificado ningún servicio.\n'
