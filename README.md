# 🛡️ AeroGuard — Sistema de Monitoreo de Drones

**Prototipo académico** para la detección, clasificación y monitoreo de posibles drones no autorizados mediante sensores simulados y visión artificial.

---

## 🚀 Inicio Rápido (Solo Frontend — Demo Inmediata)

El frontend funciona completamente con datos simulados **sin necesidad de backend ni Docker**.

1. Abre `frontend/index.html` directamente en tu navegador (Chrome/Edge/Firefox)
2. Usa las credenciales de demo que aparecen en la pantalla de login:
   - **admin** / Admin123!
   - **operator1** / Oper123!
   - **analyst1** / Anal123!

> ⚠️ Algunos navegadores bloquean módulos ES6 desde `file://`. Si tienes problemas, usa un servidor local:
> ```bash
> cd frontend
> python -m http.server 3000
> # Abre http://localhost:3000
> ```

---

## 🏗️ Arquitectura

```
┌─────────────┐    HTTP/WS    ┌──────────────────┐    SQL     ┌────────────┐
│  Frontend   │ ←──────────── │  Backend FastAPI  │ ────────── │ PostgreSQL │
│  (MVVM JS)  │               │  Python 3.11      │            └────────────┘
└─────────────┘               └──────────────────┘
                                       │  AMQP
                               ┌───────┴────────┐
                               │    RabbitMQ    │
                               └───────┬────────┘
                                       │
                        ┌──────────────┴──────────────┐
                        │                             │
               ┌────────────────┐          ┌─────────────────┐
               │  AI Service    │          │ Sensor Simulator │
               │ OpenCV + YOLO  │          │ Telemetría       │
               └────────────────┘          └─────────────────┘
```

## 📁 Estructura del Proyecto

```
AeroguardClase/
├── frontend/                    # SPA JavaScript (MVVM)
│   ├── index.html               # Punto de entrada
│   └── src/
│       ├── main.js              # Router + registro de vistas
│       ├── app.js               # Router, Layout, Toast
│       ├── models/              # Capa Modelo MVVM
│       ├── viewmodels/          # Capa ViewModel MVVM
│       ├── views/               # Capa Vista MVVM (páginas)
│       ├── services/            # API service, WebSocket, Mock
│       └── assets/css/          # Design system CSS
│
├── backend/                     # FastAPI Python
│   └── app/
│       ├── main.py              # Punto de entrada FastAPI
│       ├── core/                # Config, Seguridad, DB
│       ├── models/              # Modelos SQLAlchemy
│       ├── schemas/             # Esquemas Pydantic
│       ├── services/            # Lógica de negocio
│       ├── api/v1/endpoints/    # Endpoints REST
│       └── workers/             # Consumidores RabbitMQ
│
├── ai_service/                  # Servicio de Visión Artificial
│   └── detector.py              # OpenCV + YOLO detector
│
├── sensor_simulator/            # Simulador de telemetría
│   └── simulator.py             # Generador de datos de vuelo
│
└── docker-compose.yml           # Orquestación de servicios
```

---

## 🛠️ Instalación Completa (con Docker)

### Prerrequisitos
- Docker Desktop
- Docker Compose v2

### Pasos

```bash
# 1. Clona / navega al proyecto
cd "h:\UTS\NUEVAS TECNOLOGIAS\AeroguardClase"

# 2. Crea el archivo de variables de entorno
cp .env.example .env
# Edita .env y cambia SECRET_KEY

# 3. Levanta todos los servicios
docker compose up -d

# 4. Espera ~30 segundos y accede a:
#    Frontend:  http://localhost
#    API Docs:  http://localhost:8000/docs
#    RabbitMQ:  http://localhost:15672 (aeroguard / aeroguard_pass)
```

---

## 🔐 Seguridad

| Mecanismo | Implementación |
|---|---|
| Autenticación | OAuth 2.0 Password Flow |
| Tokens | JWT (HS256, 60min access + 7d refresh) |
| Contraseñas | bcrypt (rounds=12) |
| Integridad | SHA-256 chain en audit logs |
| Headers | X-Content-Type-Options, X-Frame-Options, X-XSS-Protection |
| Acceso | RBAC (admin / operator / analyst) |
| Estándar | OWASP Top 10 2021 |

---

## 👥 Roles

| Rol | Acceso |
|---|---|
| **Administrador** | Acceso completo: usuarios, sensores, zonas, configuración, auditoría |
| **Operador** | Dashboard, detecciones, alertas, trayectorias, zonas (solo lectura) |
| **Analista** | Historial, reportes, auditoría, exportación |

---

## 📋 Requisitos Funcionales Implementados

| RF | Descripción | Estado |
|---|---|---|
| RF-001 | Iniciar Sesión | ✅ Frontend + Backend |
| RF-002 | Cambiar Contraseña | ✅ Backend |
| RF-003 | Recuperar Contraseña | ✅ Backend |
| RF-004 | Crear Nuevo Usuario | ✅ Frontend + Backend |
| RF-005 | Listar y Editar Usuarios | ✅ Frontend + Backend |
| RF-006 | Desactivar/Activar Usuario | ✅ Frontend + Backend |
| RF-007 | Gestionar Permisos y Roles | ✅ RBAC implementado |
| RF-008 | Dashboard en Tiempo Real | ✅ Leaflet + WebSocket/Sim |
| RF-009 | Visualizar Detecciones | ✅ Frontend |
| RF-010 | Consultar Detalle | ✅ Frontend |
| RF-011 | Trayectoria de Detección | ✅ Frontend + mapa |
| RF-012 | Alerta por Zona Restringida | ✅ Lógica backend |
| RF-013 | Alerta por Comportamiento | ✅ Simulador + backend |
| RF-014 | Gestionar Alertas | ✅ Frontend completo |
| RF-015 | Crear Zona Restringida | ✅ Frontend + backend |
| RF-016 | Editar y Eliminar Zonas | ✅ Frontend + backend |
| RF-017 | Visualizar Zonas | ✅ Mapa Leaflet |
| RF-018 | Configurar Parámetros | ✅ Frontend |
| RF-019 | Activar/Desactivar Sensores | ✅ Frontend + backend |
| RF-020 | Procesar Datos de Detección | ✅ Backend + simulador |
| RF-021 | Analizar Objeto IA | ✅ AI Service (OpenCV/YOLO) |
| RF-022 | Registrar Evento | ✅ Backend |
| RF-023 | Reporte de Detecciones | ✅ Frontend (backend en extensión) |
| RF-024 | Reporte de Alertas | ✅ Frontend (backend en extensión) |
| RF-025 | Reportes Programados | ✅ Frontend + APScheduler |
| RF-026 | Exportar Histórico | ✅ Frontend (CSV/Excel) |
| RF-027 | Registrar Auditoría | ✅ Backend (SHA-256 chain) |
| RF-028 | Consultar Auditoría | ✅ Frontend |
| RF-029 | Validar Integridad | ✅ Hash SHA-256 + validación rangos |

---

## 🗺️ Google Maps (Opcional)

Para activar Google Maps además de Leaflet, edita `frontend/index.html`:

```html
window.GOOGLE_MAPS_API_KEY = 'TU_API_KEY_AQUI';
```

---

## 📊 Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | Vanilla JS + HTML/CSS (MVVM) |
| Mapa | Leaflet.js + OpenStreetMap |
| Backend | Python 3.11 + FastAPI |
| Base de datos | PostgreSQL 16 |
| Mensajería | RabbitMQ 3.13 |
| IA | Python + OpenCV + YOLOv8 |
| Contenedores | Docker + Docker Compose |
| Autenticación | OAuth 2.0 + JWT |
| API Docs | OpenAPI / Swagger |

---

## 📄 Licencia

Prototipo académico — Universidad de Tecnología de Santander (UTS).
Solo para uso educativo.
