# syntax=docker/dockerfile:1.7
# ============================================================
# AeroGuard — Backend (FastAPI) · Multi-Stage Build
#
#   builder  → compila wheels en un virtualenv aislado (gcc, libpq-dev)
#   test     → venv + deps de testing, ejecuta pytest (quality gate CI)
#   runtime  → imagen final mínima: solo venv + código, sin compiladores
#
# Build producción:  docker build --target runtime -t aeroguard-backend .
# Ejecutar tests:    docker build --target test -t aeroguard-backend:test .
# ============================================================

ARG PYTHON_VERSION=3.11

# ------------------------------------------------------------
# Stage 1: builder
# ------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Solo requirements primero → la capa de dependencias se cachea
# mientras requirements.txt no cambie.
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip wheel \
    && pip install -r requirements.txt

# ------------------------------------------------------------
# Stage 2: test (quality gate — no se publica)
# ------------------------------------------------------------
FROM builder AS test

WORKDIR /app
COPY requirements-dev.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-dev.txt

COPY . .
ENV PYTHONPATH=/app \
    APP_ENV=test
RUN python -m compileall app/ -q \
    && python -m pytest tests/ -q -p no:cacheprovider


# ------------------------------------------------------------
# Stage 3: runtime (imagen de producción)
# ------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL org.opencontainers.image.title="aeroguard-backend" \
      org.opencontainers.image.description="AeroGuard C-UAS Backend — FastAPI + PostGIS" \
      org.opencontainers.image.vendor="UTS - AeroGuard Team"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

# Solo librerías de ejecución (sin gcc ni headers):
#   libpq5     → cliente PostgreSQL
#   libglib2.0 → requerido por opencv-python-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /usr/sbin/nologin aeroguard \
    && mkdir -p /tmp/aeroguard/reports \
    && chown -R aeroguard:aeroguard /tmp/aeroguard

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=aeroguard:aeroguard app ./app
COPY --chown=aeroguard:aeroguard init.sql ./init.sql

USER aeroguard
EXPOSE 8000

# Healthcheck con Python stdlib → no hace falta instalar curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
