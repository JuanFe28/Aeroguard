# syntax=docker/dockerfile:1.7
# ============================================================
# AeroGuard — Sensor Simulator · Multi-Stage Build
# ============================================================

ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# ------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL org.opencontainers.image.title="aeroguard-simulator" \
      org.opencontainers.image.description="AeroGuard — Simulador de telemetría de sensores"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin aeroguard

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=aeroguard:aeroguard simulator.py .

USER aeroguard

CMD ["python", "simulator.py"]
