"""
AeroGuard — FastAPI Main Application
Punto de entrada del backend con configuración de seguridad, CORS, rutas y WebSocket.
"""

from contextlib import asynccontextmanager
import structlog

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.security import get_current_user

# Router imports
from app.api.v1.endpoints import (
    auth, users, detections, sensors, alerts, zones, reports, audit, config, websocket, ai
)

logger = structlog.get_logger(__name__)


# ============================================================
# Lifespan (startup / shutdown)
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("AeroGuard backend starting", env=settings.APP_ENV)

    # Initialize database tables and seed data
    from app.core.database import init_db
    try:
        await init_db()
    except Exception as e:
        logger.error("Error al inicializar la base de datos", error=str(e))

    logger.info("AeroGuard backend ready")
    yield

    # Shutdown
    logger.info("AeroGuard backend shutting down")


# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="AeroGuard API",
    description="""
    **AeroGuard** — Sistema de detección, clasificación y monitoreo de drones no autorizados.

    ## Autenticación
    Usa OAuth 2.0 con JWT. Obtén un token en `/api/v1/auth/token` y úsalo como `Bearer <token>`.

    ## Roles
    - **admin**: Acceso completo al sistema
    - **operator**: Monitoreo y gestión de alertas
    - **analyst**: Consulta, reportes y auditoría
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ============================================================
# Security Headers Middleware
# ============================================================

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses (OWASP)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]    = "nosniff"
    response.headers["X-Frame-Options"]           = "DENY"
    response.headers["X-XSS-Protection"]          = "1; mode=block"
    response.headers["Referrer-Policy"]            = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]         = "camera=(), microphone=(), geolocation=()"
    # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ============================================================
# CORS Middleware
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["Content-Disposition"],
)


# ============================================================
# Exception Handlers
# ============================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Recurso no encontrado."})

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error("Unhandled server error", path=request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Contacta al administrador."}
    )


# ============================================================
# API Routes
# ============================================================

PREFIX = settings.API_V1_PREFIX

app.include_router(auth.router,        prefix=f"{PREFIX}/auth",       tags=["Autenticación"])
app.include_router(users.router,       prefix=f"{PREFIX}/users",      tags=["Usuarios"])
app.include_router(detections.router,  prefix=f"{PREFIX}/detections", tags=["Detecciones"])
app.include_router(sensors.router,     prefix=f"{PREFIX}/sensors",    tags=["Sensores"])
app.include_router(alerts.router,      prefix=f"{PREFIX}/alerts",     tags=["Alertas"])
app.include_router(zones.router,       prefix=f"{PREFIX}/zones",      tags=["Zonas Restringidas"])
app.include_router(reports.router,     prefix=f"{PREFIX}/reports",    tags=["Reportes"])
app.include_router(audit.router,       prefix=f"{PREFIX}/audit",      tags=["Auditoría"])
app.include_router(config.router,      prefix=f"{PREFIX}/config",     tags=["Configuración"])
app.include_router(ai.router,          prefix=f"{PREFIX}/ai",         tags=["AI"])
app.include_router(websocket.router,   prefix="/ws",                  tags=["WebSocket"])


# ============================================================
# Health Check
# ============================================================

@app.get("/health", tags=["Sistema"], summary="Health check")
async def health_check():
    """Verifica el estado del sistema."""
    return {
        "status":  "healthy",
        "version": settings.APP_VERSION,
        "env":     settings.APP_ENV,
    }


@app.get("/", tags=["Sistema"], summary="Root")
async def root():
    return {
        "name":    settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs":    "/docs",
    }
