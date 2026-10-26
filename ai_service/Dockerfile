# syntax=docker/dockerfile:1.7
# ============================================================
# AeroGuard — AI Vision Service (OpenCV) · Multi-Stage Build
#   builder → instala dependencias en /opt/venv
#   runtime → solo venv + libs nativas mínimas para OpenCV headless
# ============================================================

ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip wheel \
    && pip install -r requirements.txt

# ------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL org.opencontainers.image.title="aeroguard-ai-service" \
      org.opencontainers.image.description="AeroGuard — Detector de drones OpenCV/YOLO"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# opencv-python-headless solo necesita glib y OpenMP
# (libsm6/libxext6/libxrender eran para la variante con GUI)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /usr/sbin/nologin aeroguard

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=aeroguard:aeroguard detector.py http_api.py ./ai_service/

USER aeroguard

EXPOSE 8001
ENV AI_HTTP_HOST=0.0.0.0
CMD ["python", "-m", "ai_service.detector"]
