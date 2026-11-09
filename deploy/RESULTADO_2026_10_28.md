# Resultado del despliegue privado del 28 de octubre de 2026

La candidata académica `1.2.0-rc.1` quedó instalada en el servidor real con las imágenes originales fijadas por digest. La preparación del repositorio usada fue `2f1971ffbb40e590a8025226f24690a1240213cf`; la versión del código contenido en las imágenes es `33f1cfd5aa9f7ef3d059c2dbc054f293ae4e7db1`. No se reconstruyeron las imágenes ni se cambió la candidata.

## Comprobaciones del servidor

- Ubuntu 24.04 x86_64, Docker Engine 29.9.2 y Compose 5.6.1.
- Motor rootless bajo la cuenta exclusiva `aeroguard`, sin sudo. Sus accesos por clave están restringidos al portátil autorizado; no se modificó la política global de SSH.
- Unidades nuevas del motor global bloqueadas. SSH, Samba, Tailscale y AppArmor continuaron activos.
- Cgroups v2 y driver systemd. Límites agregados: 4 GiB de RAM, 1 GiB de swap, dos CPU equivalentes y 768 tareas.
- Prueba en contenedor temporal con límites efectivos de 64 MiB de RAM, cero swap, un cuarto de CPU y 32 procesos.
- PostgreSQL/PostGIS, RabbitMQ, backend y frontend saludables. Los perfiles opcionales de IA y simulación no se activaron.
- Únicamente el frontend publica puerto y solo en `127.0.0.1:8080`. La conexión directa al puerto por la red privada falló como se esperaba; el túnel SSH permitió abrir frontend y salud desde el portátil.
- API en producción, login correcto y acceso anónimo a usuarios bloqueado.
- Un CSV de comprobación sin detecciones operativas conservó su hash después de detener y levantar todo el stack.
- El respaldo PostgreSQL se restauró en una base nueva. Coincidieron los conteos de usuarios, sensores, detecciones, auditoría y reportes. Se respaldó también el archivo original y coincidió su hash.

La evidencia pública está en [2026-10-28-server.json](evidence/2026-10-28-server.json). Los respaldos, secretos, direcciones de conexión y claves permanecen privados y no se incluyen en Git.

## Verificación del computador de desarrollo

Se preparó `.venv` con las dependencias fijadas. Las 99 pruebas funcionales, incluidas las cinco del adaptador HTTP de visión, aprobaron. También habían aprobado las once pruebas enfocadas de preparación de Deploy y los controles de sintaxis de 55 archivos Python y 16 JavaScript.

Se detectó y corrigió el aislamiento de una prueba: la comprobación del secreto predeterminado leía el `.env` privado del desarrollador y podía aceptar una clave válida ajena al caso. Ahora no lee ese archivo y prueba explícitamente el valor predeterminado, sin cambiar la validación de producción.

La prueba WebSocket de 10 y 50 clientes aprobó. La de 100 clientes registró P95 de 113,154 ms frente al objetivo de 100 ms, con cero errores y cero mensajes perdidos. Se observó también un resultado previo de 111,689 ms. No se relajó el umbral ni se presenta esa carga como aprobada. Es una medición local de Windows; el rendimiento del servidor a esa carga queda por medir.

## Alcance del cierre

DEPLOY-02 cuenta con evidencia de instalación privada, autenticación, aislamiento, persistencia y recuperación para el stack básico. Esto no acredita una evaluación completa de seguridad ni una validación operativa de detección de drones. No se reinició el anfitrión y no se alteraron firewall, router o ACL de Tailscale.

Continúan pendientes los datos sintéticos del panel SOAR, la recuperación de trabajos del scheduler, la revisión de referencias inválidas, el anclaje externo de auditoría, las integraciones SMTP/n8n y la validación con sensores y dataset independiente. Las actualizaciones pendientes del anfitrión requieren su propia revisión y no se aplicó una actualización general.
