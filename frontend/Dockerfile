# syntax=docker/dockerfile:1.7
# ============================================================
# AeroGuard — Frontend (Vanilla JS MVVM + Nginx) · Multi-Stage Build
#   assets  → copia el SPA y genera versiones .gz pre-comprimidas
#   runtime → nginx:alpine sirviendo estáticos (gzip_static) + proxy API/WS
#
# Build context: raíz del repositorio (necesita nginx.conf)
#   docker build -f frontend/Dockerfile -t aeroguard-frontend .
# ============================================================

# ------------------------------------------------------------
# Stage 1: assets
# ------------------------------------------------------------
FROM alpine:3.20 AS assets

WORKDIR /dist
COPY frontend/ ./

# Pre-compresión: nginx sirve el .gz directamente sin comprimir en cada request
RUN find . -type f \( -name '*.html' -o -name '*.js' -o -name '*.css' -o -name '*.svg' -o -name '*.json' \) \
        -exec gzip -9 -k -n {} \;

# ------------------------------------------------------------
# Stage 2: runtime
# ------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

LABEL org.opencontainers.image.title="aeroguard-frontend" \
      org.opencontainers.image.description="AeroGuard C-UAS — Dashboard táctico (Nginx)"

RUN rm -rf /usr/share/nginx/html/* /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=assets /dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q --spider http://127.0.0.1/index.html || exit 1
