# Guía Operativa, Roles RBAC y Observabilidad — AeroGuard

## 1. Control de Acceso Basado en Roles (RBAC)
- **admin:** Administración de usuarios, configuración global del sistema, re-indexación RAG, lectura/gestión total de alertas, sensores, zonas, auditoría y reportes.
- **operator:** Monitoreo operativo, ingesta y consulta de detecciones, creación, asignación y resolución de alertas, disparo de flujo SOAR (`/trigger-incident`), lectura de zonas y sensores. **No** administra usuarios ni credenciales ni reconfigura secretos.
- **analyst:** Consulta de detecciones, alertas, zonas, trazabilidad histórica, auditoría y generación/descarga de reportes PDF/CSV/Excel. **No** modifica alertas ni ejecuta acciones operativas de escritura en sensores/usuarios.

## 2. Seguridad y Privacidad
- Las contraseñas usan **bcrypt**; la autenticación usa JWT con revocación persistente por versión en `auth_state`. Ningún endpoint ni agente debe exponer `password_hash`, `SECRET_KEY`, tokens de sesión o contraseñas de otros usuarios.
- En despliegue Oracle Cloud (4 GiB RAM / 2 vCPU, `x86_64` y `ARM64`), el servicio corre detrás de Nginx loopback (`127.0.0.1:8080`), con Qdrant en modo embebido local (`volume qdrant_data`), RabbitMQ para procesamiento asíncrono y Prometheus/Grafana en `/metrics` protegido por token o permiso `config:read`.
