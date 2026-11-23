"""
AeroGuard — Observabilidad LLMOps para el Módulo Agéntico

Registra:
- Métricas Prometheus en /metrics (requests, latencia P95, bloqueos de Guardrails, hits RAG y tokens).
- Trazas persistentes en la tabla agent_traces (PostgreSQL / SQLite).
- Hook opcional no bloqueante hacia OTEL_EXPORTER_OTLP_ENDPOINT / LangSmith cuando están activos.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence
import httpx
import structlog
from prometheus_client import Counter, Histogram
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import AgentTrace

logger = structlog.get_logger(__name__)

AGENT_REQUESTS = Counter(
    "aeroguard_agent_requests_total",
    "Total de ejecuciones del grafo agéntico",
    ["provider", "status"],
)
AGENT_LATENCY = Histogram(
    "aeroguard_agent_latency_seconds",
    "Latencia total de ejecución del agente IA en segundos",
    ["provider"],
)
AGENT_GUARDRAIL_BLOCKS = Counter(
    "aeroguard_agent_guardrail_blocks_total",
    "Bloqueos activados por los Guardrails de entrada o salida",
    ["stage", "reason"],
)
AGENT_RAG_HITS = Counter(
    "aeroguard_agent_rag_hits_total",
    "Fragmentos recuperados desde Qdrant RAG",
)
AGENT_TOKENS_EST = Counter(
    "aeroguard_agent_tokens_estimated_total",
    "Tokens estimados procesados por el agente",
    ["provider"],
)


def record_agent_metrics(
    provider: str,
    status: str,
    total_latency_ms: float,
    rag_hits: int,
    estimated_tokens: int,
    guardrail_in_passed: bool,
    guardrail_out_passed: bool,
    block_category: str = "policy",
) -> None:
    """Actualiza contadores e histograma de Prometheus."""
    AGENT_REQUESTS.labels(provider=provider, status=status).inc()
    AGENT_LATENCY.labels(provider=provider).observe(max(0.0, total_latency_ms / 1000.0))
    if rag_hits > 0:
        AGENT_RAG_HITS.inc(rag_hits)
    if estimated_tokens > 0:
        AGENT_TOKENS_EST.labels(provider=provider).inc(estimated_tokens)
    if not guardrail_in_passed:
        AGENT_GUARDRAIL_BLOCKS.labels(stage="input", reason=block_category or "input_policy").inc()
    if not guardrail_out_passed:
        AGENT_GUARDRAIL_BLOCKS.labels(stage="output", reason=block_category or "output_policy").inc()


async def persist_agent_trace(
    db: AsyncSession,
    *,
    session_id: str | None,
    username: str,
    role: str,
    provider: str,
    engine: str,
    guardrail_in_passed: bool,
    guardrail_out_passed: bool,
    blocked_reason: str | None,
    rag_hits: int,
    tools_called: Sequence[str],
    node_latencies_ms: Mapping[str, float],
    total_latency_ms: float,
    estimated_tokens: int,
    status: str,
) -> AgentTrace:
    """Guarda la traza auditable del ciclo agéntico en BD y dispara hook OTLP opcional."""
    trace = AgentTrace(
        session_id=session_id,
        username=username,
        role=role,
        provider=provider,
        engine=engine,
        guardrail_in_passed=guardrail_in_passed,
        guardrail_out_passed=guardrail_out_passed,
        blocked_reason=blocked_reason,
        rag_hits=rag_hits,
        tools_called=list(tools_called),
        node_latencies_ms=dict(node_latencies_ms),
        total_latency_ms=round(float(total_latency_ms), 2),
        estimated_tokens=int(estimated_tokens),
        status=status,
    )
    db.add(trace)
    await db.flush()

    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        await _emit_optional_otlp_span(trace)

    return trace


async def _emit_optional_otlp_span(trace: AgentTrace) -> None:
    """Envío no bloqueante de telemetría externa si OTEL/Phoenix está configurado."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(
                settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                json={
                    "service": "aeroguard-agent",
                    "trace_id": trace.id,
                    "provider": trace.provider,
                    "engine": trace.engine,
                    "status": trace.status,
                    "latency_ms": trace.total_latency_ms,
                    "tools_called": trace.tools_called,
                    "rag_hits": trace.rag_hits,
                },
            )
    except Exception as exc:
        logger.debug("Telemetría OTLP externa opcional omitida", error=str(exc))


async def get_llmops_summary(db: AsyncSession) -> dict[str, Any]:
    """Calcula métricas agregadas de LLMOps sobre la tabla agent_traces."""
    total_runs = (await db.execute(select(func.count()).select_from(AgentTrace))).scalar_one()
    blocked_in = (
        await db.execute(select(func.count()).select_from(AgentTrace).where(AgentTrace.guardrail_in_passed.is_(False)))
    ).scalar_one()
    blocked_out = (
        await db.execute(select(func.count()).select_from(AgentTrace).where(AgentTrace.guardrail_out_passed.is_(False)))
    ).scalar_one()
    avg_latency = (
        await db.execute(select(func.avg(AgentTrace.total_latency_ms)))
    ).scalar_one()
    total_tokens = (
        await db.execute(select(func.sum(AgentTrace.estimated_tokens)))
    ).scalar_one()

    recent_rows = (
        await db.execute(select(AgentTrace).order_by(desc(AgentTrace.created_at)).limit(10))
    ).scalars().all()

    return {
        "total_runs": int(total_runs or 0),
        "blocked_input_count": int(blocked_in or 0),
        "blocked_output_count": int(blocked_out or 0),
        "avg_latency_ms": round(float(avg_latency or 0.0), 2),
        "total_estimated_tokens": int(total_tokens or 0),
        "langsmith_enabled": bool(settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY),
        "otlp_enabled": bool(settings.OTEL_EXPORTER_OTLP_ENDPOINT),
        "recent_traces": [
            {
                "id": t.id,
                "session_id": t.session_id,
                "username": t.username,
                "role": t.role,
                "provider": t.provider,
                "engine": t.engine,
                "status": t.status,
                "guardrail_in_passed": t.guardrail_in_passed,
                "guardrail_out_passed": t.guardrail_out_passed,
                "rag_hits": t.rag_hits,
                "tools_called": t.tools_called,
                "total_latency_ms": t.total_latency_ms,
                "estimated_tokens": t.estimated_tokens,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in recent_rows
        ],
    }
