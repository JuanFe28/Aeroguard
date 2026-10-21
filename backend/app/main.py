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
from fastapi import Response
from app.core.security import require_permission
from app.core.security import oauth2_scheme, get_user_from_token, has_permission
from fastapi import HTTPException
import secrets
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time

REQUESTS = Counter("aeroguard_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("aeroguard_http_request_seconds", "HTTP duration", ["method", "route"])
SENSORS_STALE = Gauge("aeroguard_sensors_stale", "Active sensors without recent telemetry")

from app.core.config import settings
from app.core.security import get_current_user

# Router imports
from app.api.v1.endpoints import (
    auth, users, detections, sensors, alerts, zones, reports, audit, config, websocket, ai
)

logger = structlog.get_logger(__name__)
from app.core.logging_security import install_log_redaction
install_log_redaction()


# ============================================================
# Lifespan (startup / shutdown)
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("AeroGuard backend starting", env=settings.APP_ENV)

    # Initialize database tables and seed data
    from app.core.database import init_db
    await init_db()
    from app.core import database
    async with database.AsyncSessionLocal() as db:
        await config.load_persisted_config(db)
    app.state.database_initialized = True
    import asyncio
    from app.services.report_scheduler_service import scheduler_loop
    scheduler = asyncio.create_task(scheduler_loop()) if settings.REPORT_SCHEDULER_ENABLED else None

    logger.info("AeroGuard backend ready")
    try:
        yield
    finally:
        if scheduler:
            scheduler.cancel()
            try:
                await scheduler
            except asyncio.CancelledError:
                pass

    # Shutdown
    logger.info("AeroGuard backend shutting down")
    app.state.database_initialized = False


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


@app.middleware("http")
async def observe_and_limit_auth(request: Request, call_next):
    start = time.perf_counter()
    limited_paths = {"/api/v1/auth/token", "/api/v1/auth/request-reset", "/api/v1/auth/reset-password"}
    if request.method == "POST" and request.url.path in limited_paths:
        from app.core.database import AsyncSessionLocal
        from app.services.session_service import allow_auth_attempt
        try:
            async with AsyncSessionLocal() as db:
                allowed = await allow_auth_attempt(db, request.client.host if request.client else "unknown", request.url.path)
        except Exception:
            return JSONResponse(status_code=503, content={"detail": "Autenticación temporalmente no disponible."})
        if not allowed:
            return JSONResponse(status_code=429, content={"detail": "Demasiados intentos. Intenta más tarde."},
                                headers={"Retry-After": str(settings.AUTH_RATE_WINDOW_SECONDS)})
    response = await call_next(request)
    route = request.scope.get("route")
    route_label = getattr(route, "path", "unmatched")
    REQUESTS.labels(request.method, route_label, str(response.status_code)).inc()
    LATENCY.labels(request.method, route_label).observe(time.perf_counter() - start)
    return response


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
    expose_headers=["Content-Disposition", "X-Report-SHA256", "X-Content-SHA256", "X-AeroGuard-Data-Source"],
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


@app.get("/ready", tags=["Sistema"])
async def readiness():
    from app.core import database
    from sqlalchemy import text, select, func
    try:
        async with database.AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            from app.models.models import Sensor, SensorStatus
            from datetime import datetime, timezone, timedelta
            stale = (await db.execute(select(func.count()).select_from(Sensor).where(
                Sensor.status == SensorStatus.ACTIVE,
                (Sensor.last_active < datetime.now(timezone.utc) - timedelta(seconds=settings.SENSOR_STALE_SECONDS)) | Sensor.last_active.is_(None),
            ))).scalar_one()
            SENSORS_STALE.set(stale)
        return {"status": "ready", "database": database.engine.dialect.name, "stale_sensors": stale}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready", "database": "unavailable"})


async def require_metrics_access(token: str = Depends(oauth2_scheme)):
    if len(settings.METRICS_BEARER_TOKEN) >= 32 and secrets.compare_digest(token, settings.METRICS_BEARER_TOKEN):
        return
    user = await get_user_from_token(token)
    if not has_permission(user.role, 'config:read'):
        raise HTTPException(403, 'Permiso de monitoreo requerido.')


@app.get("/metrics", include_in_schema=False)
async def metrics(current_user=Depends(require_metrics_access)):
    return Response(content=generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})
