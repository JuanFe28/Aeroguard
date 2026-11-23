# Despliegue de AeroGuard en Oracle Cloud (Módulo A + Módulo B Agéntico)

Guía operativa para desplegar el stack completo de AeroGuard (`backend` FastAPI + CRISP-DM ML + LangGraph + RAG Qdrant + Guardrails + LLMOps, `frontend` Nginx SPA, `postgres` PostGIS y `rabbitmq`) dentro de un servidor Oracle Cloud bajo el **techo de diseño de 4 GiB RAM y 2 vCPU**, compatible tanto con **`x86_64` (AMD64)** como con **Oracle Ampere `ARM64` (`aarch64`)**.

---

## 1. Presupuesto de Memoria RAM y vCPU

El perfil base en `deploy/compose.oracle.yml` evita levantar un contenedor vectorial extra gracias a **`qdrant-client` en modo local embebido** persistido en el volumen `qdrant_data`, y utiliza embeddings deterministas livianos (`512` dimensiones en NumPy, sin PyTorch ni `sentence-transformers`).

| Servicio / Perfil | Modo | RAM (`mem_limit`) | vCPU (`cpus`) | Red |
| --- | --- | --- | --- | --- |
| `postgres` (`postgis/postgis:16-3.5`) | Base | `768 MiB` | `0.50` | `default` (interna) |
| `rabbitmq` (`rabbitmq:4.3.6-management-alpine`) | Base | `384 MiB` | `0.30` | `default` (interna) |
| `backend` (FastAPI + LangGraph + Qdrant embebido + ML) | Base | `1024 MiB` (`1 GiB`) | `0.85` | `default`, `egress` |
| `frontend` (Nginx SPA) | Base | `128 MiB` | `0.15` | `default`, `entry` (`127.0.0.1:8080`) |
| **Total stack base** | **Base (4 servicios)** | **`2304 MiB` (~2.25 GiB)** | **`1.80`** | Listo para SOAR/Agente |
| `prometheus` (`compose.monitoring.yml`) | Opcional monitoreo | `256 MiB` | `0.25` | `default`, `entry` |
| `grafana` (`compose.monitoring.yml`) | Opcional monitoreo | `256 MiB` | `0.25` | `default`, `entry` |
| **Total base + monitoreo LLMOps** | **Observabilidad** | **`2816 MiB` (~2.75 GiB)** | **`2.30` nominal (`< 2 vCPU` reales en reposo)** | Bajo techo 4 GiB |
| `qdrant` (`--profile qdrant-external`) | Opcional escalado | `256 MiB` | `0.25` | `default` (interna) |
| `ai-worker` (`--profile ai`) | Opcional detección | `512 MiB` | `0.50` | `default` |
| `tunnel` (`--profile tunnel`) | Opcional enlace HTTPS público | `96 MiB` | `0.15` | `default`, `egress` |

> [!NOTE]
> El almacenamiento vectorial local de `qdrant_data:/tmp/aeroguard/qdrant` comparte el contenedor `backend` y permite escalar sin cambios de código activando `--profile qdrant-external` y definiendo `QDRANT_URL=http://qdrant:6333` en `deploy/.env`.

---

## 2. Compatibilidad `x86_64` y Oracle Ampere `ARM64` (`aarch64`)

1. **`backend` y `frontend`:** Se construyen localmente multi-arquitectura con `backend/Dockerfile` (`INSTALL_AGENT_DEPS=true`, que añade `backend/requirements-agent.txt`: `langgraph`, `langchain-core`, `qdrant-client`) y `frontend/Dockerfile`. No instalan `torch` ni librerías pesadas de GPU/transformers.
2. **`rabbitmq:4.3.6-management-alpine` y `qdrant/qdrant:v1.13.6`:** Publican imágenes nativas `linux/amd64` y `linux/arm64`.
3. **PostgreSQL + PostGIS (`POSTGIS_IMAGE`):** Por defecto usa `postgis/postgis:16-3.5` (igual que `deploy/compose.yml`). En instancias Oracle Ampere `ARM64` donde se prefiera una imagen multi-arch nativa de PostGIS para ARM64 (p. ej. `imresamu/postgis:16-3.5` o equivalente verificado en tu entorno), basta definir en `deploy/.env`:
   ```env
   POSTGIS_IMAGE=postgis/postgis:16-3.5
   ```
   sin modificar ningún archivo YAML ni la imagen del stack base del equipo.

---

## 3. Configuración del Proveedor LLM (DeepSeek + Fallback Determinista)

En `deploy/.env` (basado en `.env.example`):

- **Con DeepSeek API (OpenAI-compatible):**
  ```env
  AGENT_ENABLED=true
  LLM_PROVIDER=deepseek
  DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
  DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
  DEEPSEEK_MODEL=deepseek-chat
  LLM_TIMEOUT_SECONDS=12.0
  ```
- **Sin API key / entorno offline / pruebas CI:**
  ```env
  AGENT_ENABLED=true
  LLM_PROVIDER=deterministic
  DEEPSEEK_API_KEY=
  ```
  El grafo `LangGraph` en `backend/app/services/agent_graph_service.py` realiza **fallback determinista automático** si falta `DEEPSEEK_API_KEY`, si el proveedor responde error o si expira `LLM_TIMEOUT_SECONDS`, aplicando los mismos Guardrails de Entrada/Salida y citas RAG verificadas.

---

## 4. Arranque, Persistencia RAG y Monitoreo LLMOps

1. **Generar secretos de producción** (si no existe `deploy/.env`):
   ```bash
   python3 scripts/prepare_deploy.py
   ```
2. **Levantar el stack Oracle Cloud (con build de dependencias agénticas):**
   ```bash
   docker compose --env-file deploy/.env -f deploy/compose.oracle.yml up -d --build
   ```
3. **Verificar salud e indexación inicial RAG:**
   - Endpoint de salud: `http://127.0.0.1:8080/health` (vía Nginx frontend -> backend).
   - El corpus `docs/conocimiento_cuas/*.md` se monta en solo lectura (`/workspace/docs/conocimiento_cuas:ro`) y se reindexa automáticamente cada `RAG_REINDEX_INTERVAL_MINUTES` (por defecto `60` minutos) mediante `APScheduler` (`rag_scheduler_service.py`), además de poder invocarse manualmente con `POST /api/v1/agent/rag/reindex` (`admin` / `operator`).
4. **Activar Prometheus + Grafana (con alertas y paneles de Guardrails/Latencia del Agente):**
   ```bash
   python3 scripts/prepare_monitoring.py
   docker compose --env-file deploy/.env -f deploy/compose.oracle.yml -f deploy/compose.monitoring.yml up -d
   ```
   - Panel Grafana en `127.0.0.1:13000` (túnel SSH recomendado: `ssh -L 13000:127.0.0.1:13000 usuario@oracle-ip`).
   - Alertas configuradas en `monitoring/rules.yml`: `AeroGuardAgentHighGuardrailBlocks` y `AeroGuardAgentHighLatency`.
   - Trazabilidad externa opcional (no bloqueante): define `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` o `OTEL_EXPORTER_OTLP_ENDPOINT` para exportar spans `AgentTrace`.

---

## 5. Seguridad de Red en Oracle Cloud

- `postgres`, `rabbitmq` y `qdrant` (opcional) viven exclusivamente en la red `default` (`internal: true`), sin puertos publicados ni salida a Internet.
- `frontend` publica únicamente `127.0.0.1:${HTTP_PORT:-8080}:80`; expón el puerto público en Oracle mediante el perfil `--profile tunnel` (Cloudflare Quick Tunnel HTTPS), Caddy/Nginx TLS en el host o Security Lists restringidas + túnel SSH.
- `backend` usa `read_only: true`, `cap_drop: [ALL]`, `no-new-privileges:true` y solo escribe en `/tmp` (`tmpfs`), `reports_data` (`/tmp/aeroguard/reports`) y `qdrant_data` (`/tmp/aeroguard/qdrant`).

### 5.1 Enlace Público HTTPS sin Comandos desde el PC (`--profile tunnel`)

Para acceder a AeroGuard directamente desde cualquier navegador sin abrir puertos del firewall ni ejecutar túneles SSH desde el PC:

1. **Activar el perfil `tunnel` (`cloudflare/cloudflared:latest`):**
   ```bash
   docker compose --env-file deploy/.env -f deploy/compose.oracle.yml --profile tunnel up -d
   ```
   *(Con monitoreo incluido, añade `--env-file deploy/.env.monitoring -f deploy/compose.monitoring.yml`.)* El contenedor `tunnel` se conecta tanto a la red interna `default` (para alcanzar `http://frontend:80`) como a `egress` (para publicar el túnel cifrado hacia Cloudflare).
2. **Obtener la URL pública generada:**
   ```bash
   docker logs aeroguard-oracle-tunnel-1 | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -n 1
   ```
3. **Autorizar la URL en `PUBLIC_FRONTEND_URL` y `BACKEND_CORS_ORIGINS` (`deploy/.env`) y recargar `backend`:**
   ```env
   PUBLIC_FRONTEND_URL=https://<subdominio>.trycloudflare.com
   BACKEND_CORS_ORIGINS=["http://localhost:8080","https://<subdominio>.trycloudflare.com"]
   ```
   ```bash
   docker compose --env-file deploy/.env -f deploy/compose.oracle.yml --profile tunnel up -d --force-recreate --no-deps backend
   ```

> [!IMPORTANT]
> Un Cloudflare Quick Tunnel (`*.trycloudflare.com`) mantiene la URL activa mientras el contenedor permanezca encendido, pero asigna un subdominio aleatorio distinto si el contenedor `tunnel` se recrea o reinicia desde cero. Para una URL fija permanente, sustituye el comando por un Cloudflare Named Tunnel (`tunnel run --token ...`) asociado a un dominio propio.
