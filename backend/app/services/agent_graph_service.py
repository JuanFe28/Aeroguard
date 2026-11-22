"""
AeroGuard — Orquestador Agéntico LangGraph (LLM + Herramientas + Memoria + Bucle)

Flujo de producción explícito:
  perceive -> guardrail_in -> (blocked -> finalize_blocked | ok -> retrieve_rag
  -> plan_and_tools -> reason_llm -> guardrail_out) -> persist_and_trace -> END

Soporta DeepSeek API (OpenAI-compatible) con fallback determinista local automático.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Literal, Mapping, Optional, TypedDict

import httpx
import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import has_permission
from app.models.models import AgentMessage, AgentSession
from app.services.agent_guardrails import evaluate_input_guardrail, evaluate_output_guardrail
from app.services.agent_llmops import persist_agent_trace, record_agent_metrics
from app.services.agent_rag_service import agent_rag_service
from app.services.agent_tools import (
    run_dispatch_soar_tool,
    run_forecast_tool,
    run_goal_agent_tool,
    run_operational_snapshot_tool,
    run_predictive_ml_tool,
)

logger = structlog.get_logger(__name__)

try:
    from langchain_core.runnables import RunnableConfig
    from langgraph.graph import END, StateGraph

    HAS_LANGGRAPH = True
except ImportError:  # pragma: no cover - fallback solo si falta wheel opcional
    RunnableConfig = dict  # type: ignore[misc, assignment]
    END = "__end__"
    StateGraph = None
    HAS_LANGGRAPH = False


class AgentGraphState(TypedDict, total=False):
    query: str
    session_id: Optional[str]
    username: str
    user_id: str
    user_role: str
    telemetry: Optional[dict[str, Any]]
    zone: Optional[dict[str, Any]]
    dispatch_event: bool
    memory_history: list[dict[str, str]]
    guardrail_in_passed: bool
    guardrail_in_category: str
    guardrail_in_reason: str
    rag_citations: list[dict[str, Any]]
    tools_called: list[str]
    tool_outputs: dict[str, Any]
    candidate_output: dict[str, Any]
    provider: str
    estimated_tokens: int
    guardrail_out_passed: bool
    guardrail_out_reason: str
    final_output: dict[str, Any]
    status: str
    node_latencies_ms: dict[str, float]
    total_latency_ms: float
    trace_id: Optional[str]
    vector_backend: str


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 2)


def _route_after_guardrail_in(state: AgentGraphState) -> Literal["blocked", "allowed"]:
    return "allowed" if state.get("guardrail_in_passed") else "blocked"


async def _node_perceive(state: AgentGraphState, config: RunnableConfig) -> dict[str, Any]:
    t0 = time.perf_counter()
    cfg = (config or {}).get("configurable", {})
    db: Optional[AsyncSession] = cfg.get("db")
    history: list[dict[str, str]] = []
    session_id = state.get("session_id")

    if db is not None and session_id:
        sess = await db.get(AgentSession, session_id)
        if sess is not None and (sess.user_id == state["user_id"] or state["user_role"] == "admin"):
            msgs = (
                await db.execute(
                    select(AgentMessage)
                    .where(AgentMessage.session_id == session_id)
                    .order_by(desc(AgentMessage.created_at))
                    .limit(4)
                )
            ).scalars().all()
            history = [{"sender": m.sender, "content": m.content[:300]} for m in reversed(msgs)]

    lat = dict(state.get("node_latencies_ms") or {})
    lat["perceive"] = _elapsed_ms(t0)
    return {"memory_history": history, "node_latencies_ms": lat}


async def _node_guardrail_in(state: AgentGraphState, config: RunnableConfig) -> dict[str, Any]:
    t0 = time.perf_counter()
    res = evaluate_input_guardrail(
        query=state.get("query", ""),
        user_role=state.get("user_role", "analyst"),
        dispatch_requested=bool(state.get("dispatch_event", False)),
    )
    lat = dict(state.get("node_latencies_ms") or {})
    lat["guardrail_in"] = _elapsed_ms(t0)
    return {
        "guardrail_in_passed": res.passed,
        "guardrail_in_category": res.category,
        "guardrail_in_reason": res.reason,
        "query": res.sanitized_query or state.get("query", ""),
        "node_latencies_ms": lat,
    }


async def _node_finalize_blocked(state: AgentGraphState, config: RunnableConfig) -> dict[str, Any]:
    t0 = time.perf_counter()
    reason = state.get("guardrail_in_reason") or "Consulta rechazada por política de seguridad."
    blocked_out = {
        "summary": reason,
        "recommended_action": "BLOQUEADO_POR_GUARDRAIL",
        "priority": "BLOCKED",
        "confidence_note": f"Guardrail de entrada activado ({state.get('guardrail_in_category', 'policy')}).",
        "citations": [],
        "tools_used": [],
        "human_review_required": True,
        "grounding_verified": True,
    }
    lat = dict(state.get("node_latencies_ms") or {})
    lat["finalize_blocked"] = _elapsed_ms(t0)
    return {
        "final_output": blocked_out,
        "guardrail_out_passed": True,
        "guardrail_out_reason": "blocked_at_input",
        "provider": "guardrail_policy",
        "status": "blocked_input",
        "rag_citations": [],
        "tools_called": [],
        "tool_outputs": {},
        "estimated_tokens": 0,
        "node_latencies_ms": lat,
    }


async def _node_retrieve_rag(state: AgentGraphState, config: RunnableConfig) -> dict[str, Any]:
    t0 = time.perf_counter()
    citations = agent_rag_service.search(state["query"], top_k=4)
    st = agent_rag_service.status()
    lat = dict(state.get("node_latencies_ms") or {})
    lat["retrieve_rag"] = _elapsed_ms(t0)
    return {
        "rag_citations": citations,
        "vector_backend": st["vector_backend"],
        "node_latencies_ms": lat,
    }


async def _node_plan_and_tools(state: AgentGraphState, config: RunnableConfig) -> dict[str, Any]:
    t0 = time.perf_counter()
    cfg = (config or {}).get("configurable", {})
    db: Optional[AsyncSession] = cfg.get("db")
    role = state.get("user_role", "analyst")
    query_lower = state["query"].lower()

    tools_called: list[str] = []
    tool_outputs: dict[str, Any] = {}

    snapshot = await run_operational_snapshot_tool(db, role)
    tools_called.append("get_operational_snapshot")
    tool_outputs["operational_snapshot"] = snapshot

    if any(k in query_lower for k in ("arima", "pronostico", "pronóstico", "pico", "tendencia", "futuro", "dias", "días")):
        tools_called.append("get_incursion_forecast")
        tool_outputs["arima_forecast"] = run_forecast_tool()

    telemetry = state.get("telemetry")
    if telemetry:
        zone = state.get("zone") or {"name": "Zona Evaluada", "max_allowed_altitude_m": 120.0}
        tools_called.append("evaluate_goal_agent")
        tool_outputs["goal_decision"] = run_goal_agent_tool(telemetry, zone)

        ml_payload = {
            "altitude_m": telemetry.get("altitude_m", 120.0),
            "speed_ms": telemetry.get("speed_ms", 12.0),
            "distance_to_zone_m": telemetry.get("distance_to_zone_m", 250.0),
            "rf_signal_dbm": telemetry.get("rf_signal_dbm", -70.0),
            "ai_confidence": telemetry.get("ai_confidence") if telemetry.get("ai_confidence") is not None else 0.85,
            "drone_class": telemetry.get("drone_class", "quadcopter"),
            "flight_pattern": telemetry.get("flight_pattern", "Directo"),
        }
        tools_called.append("predict_telemetry_ml")
        tool_outputs["predictive_ml"] = run_predictive_ml_tool(ml_payload)

        if state.get("dispatch_event"):
            soar_payload = {
                "event_type": "AGENT_ORCHESTRATED_INCIDENT",
                "incident_id": f"AG-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                "drone": telemetry,
                "zone": zone,
            }
            tools_called.append("dispatch_soar_event")
            tool_outputs["soar_dispatch"] = await run_dispatch_soar_tool(soar_payload, role)

    lat = dict(state.get("node_latencies_ms") or {})
    lat["plan_and_tools"] = _elapsed_ms(t0)
    return {"tools_called": tools_called, "tool_outputs": tool_outputs, "node_latencies_ms": lat}


def _deterministic_reason(state: AgentGraphState) -> dict[str, Any]:
    citations = state.get("rag_citations") or []
    tools = state.get("tool_outputs") or {}
    goal = tools.get("goal_decision")
    ml = tools.get("predictive_ml")
    fc = tools.get("arima_forecast")
    snap = tools.get("operational_snapshot") or {}

    parts: list[str] = []
    action = "MONITOREAR"
    priority = "NORMAL"

    if goal:
        action = str(goal.get("action", "VERIFICAR_DETECCION"))
        raw_prio = str(goal.get("priority", "NORMAL"))
        priority = "MEDIUM" if raw_prio == "REVIEW" else raw_prio
        parts.append(f"Motor por objetivos: {action} ({goal.get('explanation', '')})")

    if ml:
        parts.append(
            f"Analítica ML (Random Forest={ml['threat_level']}, RiskScore={ml['risk_score']}/100, "
            f"Prob. alto riesgo={ml['geofence_breach_probability']*100:.1f}%, perfil='{ml['flight_profile']}')."
        )
        if ml["threat_level"] == "CRITICAL" and priority in {"NORMAL", "MEDIUM"}:
            priority = "HIGH"

    if fc and fc.get("peak_forecast_14d"):
        pk = fc["peak_forecast_14d"]
        parts.append(
            f"Pronóstico {fc['model']}: pico estimado de ~{pk['predicted_high_risk']} eventos/día para {pk['date']}."
        )

    if snap.get("available"):
        parts.append(
            f"Estado operativo actual: {snap.get('active_zones_count', 'N/D')} zonas activas, "
            f"{snap.get('active_sensors_count', 'N/D')} sensores activos y {snap.get('open_alerts_count', 'N/D')} alertas abiertas."
        )

    if citations:
        top_c = citations[0]
        parts.append(f"Protocolo recuperado ({top_c['source']} · {top_c['section']}): {top_c['snippet'][:180]}")

    summary = " ".join(parts).strip() or "Consulta procesada con respaldo documental C-UAS."
    cite_ids = [c["doc_id"] for c in citations[:3] if c.get("doc_id")]
    return {
        "summary": summary[:2400],
        "recommended_action": action,
        "priority": priority,
        "confidence_note": "Evaluación determinista fundamentada en herramientas verificables y corpus RAG (sujeta a revisión humana).",
        "citations": cite_ids,
        "tools_used": list(state.get("tools_called") or []),
        "human_review_required": True,
    }


async def _call_deepseek_if_configured(state: AgentGraphState) -> tuple[dict[str, Any] | None, str, int]:
    provider_cfg = settings.LLM_PROVIDER.strip().lower()
    if provider_cfg not in {"deepseek", "openai"} or not settings.DEEPSEEK_API_KEY:
        return None, "deterministic", 0

    system_prompt = (
        "Eres el asistente táctico defensivo de AeroGuard C-UAS. Responde estrictamente en JSON con las claves: "
        "summary, recommended_action, priority (NORMAL|MEDIUM|HIGH|CRITICAL|INDETERMINATE), confidence_note, citations. "
        "Usa únicamente datos observados en tools y citas RAG. Prohibido recomendar jamming, inhibición RF o derribo."
    )
    user_context = {
        "query": state["query"],
        "history": state.get("memory_history") or [],
        "rag_citations": state.get("rag_citations") or [],
        "tool_outputs": state.get("tool_outputs") or {},
    }
    url = f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.DEEPSEEK_MODEL,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_context, ensure_ascii=False)},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code == 200:
                payload = resp.json()
                raw_txt = payload["choices"][0]["message"]["content"]
                parsed = json.loads(raw_txt)
                usage = payload.get("usage") or {}
                tokens = int(usage.get("total_tokens") or max(1, len(raw_txt) // 4))
                return parsed, "deepseek", tokens
    except Exception as exc:
        logger.warning("DeepSeek API no disponible; activando fallback determinista", error=str(exc))

    return None, "deterministic_fallback", 0


async def _node_reason_llm(state: AgentGraphState, config: RunnableConfig) -> dict[str, Any]:
    t0 = time.perf_counter()
    llm_parsed, provider_used, tokens = await _call_deepseek_if_configured(state)
    if llm_parsed is None:
        candidate = _deterministic_reason(state)
        tokens = tokens or max(40, (len(state["query"]) + len(candidate["summary"])) // 4)
    else:
        candidate = llm_parsed
        candidate.setdefault("tools_used", list(state.get("tools_called") or []))

    lat = dict(state.get("node_latencies_ms") or {})
    lat["reason_llm"] = _elapsed_ms(t0)
    return {
        "candidate_output": candidate,
        "provider": provider_used,
        "estimated_tokens": tokens,
        "node_latencies_ms": lat,
    }


async def _node_guardrail_out(state: AgentGraphState, config: RunnableConfig) -> dict[str, Any]:
    t0 = time.perf_counter()
    res = evaluate_output_guardrail(
        candidate=state.get("candidate_output") or {},
        rag_citations=state.get("rag_citations") or [],
        tools_used=state.get("tools_called") or [],
    )
    lat = dict(state.get("node_latencies_ms") or {})
    lat["guardrail_out"] = _elapsed_ms(t0)
    return {
        "final_output": res.output.model_dump(),
        "guardrail_out_passed": res.passed,
        "guardrail_out_reason": res.reason,
        "status": "completed" if res.passed else "blocked_output",
        "node_latencies_ms": lat,
    }


async def _node_persist_and_trace(state: AgentGraphState, config: RunnableConfig) -> dict[str, Any]:
    t0 = time.perf_counter()
    cfg = (config or {}).get("configurable", {})
    db: Optional[AsyncSession] = cfg.get("db")
    session_id = state.get("session_id")
    final_out = state.get("final_output") or {}

    lat = dict(state.get("node_latencies_ms") or {})
    lat["persist_and_trace"] = _elapsed_ms(t0)
    total_ms = round(sum(lat.values()), 2)

    trace_id: Optional[str] = None
    if db is not None:
        sess = await db.get(AgentSession, session_id) if session_id else None
        if sess is None:
            sess = AgentSession(
                user_id=state["user_id"],
                username=state["username"],
                role=state["user_role"],
                title=state["query"][:120],
            )
            db.add(sess)
            await db.flush()
            session_id = sess.id

        db.add(
            AgentMessage(
                session_id=session_id,
                sender="operator",
                content=state["query"],
                metadata_json={"role": state["user_role"]},
            )
        )
        db.add(
            AgentMessage(
                session_id=session_id,
                sender="agent" if state.get("guardrail_in_passed") and state.get("guardrail_out_passed") else "guardrail",
                content=str(final_out.get("summary", "")),
                metadata_json=final_out,
            )
        )
        blocked_reason = None
        if not state.get("guardrail_in_passed"):
            blocked_reason = state.get("guardrail_in_reason")
        elif not state.get("guardrail_out_passed"):
            blocked_reason = state.get("guardrail_out_reason")

        trace = await persist_agent_trace(
            db,
            session_id=session_id,
            username=state["username"],
            role=state["user_role"],
            provider=state.get("provider", "deterministic"),
            engine="langgraph" if HAS_LANGGRAPH else "sequential_fallback",
            guardrail_in_passed=bool(state.get("guardrail_in_passed", True)),
            guardrail_out_passed=bool(state.get("guardrail_out_passed", True)),
            blocked_reason=blocked_reason,
            rag_hits=len(state.get("rag_citations") or []),
            tools_called=state.get("tools_called") or [],
            node_latencies_ms=lat,
            total_latency_ms=total_ms,
            estimated_tokens=int(state.get("estimated_tokens", 0)),
            status=str(state.get("status", "completed")),
        )
        trace_id = trace.id

    record_agent_metrics(
        provider=state.get("provider", "deterministic"),
        status=str(state.get("status", "completed")),
        total_latency_ms=total_ms,
        rag_hits=len(state.get("rag_citations") or []),
        estimated_tokens=int(state.get("estimated_tokens", 0)),
        guardrail_in_passed=bool(state.get("guardrail_in_passed", True)),
        guardrail_out_passed=bool(state.get("guardrail_out_passed", True)),
        block_category=str(state.get("guardrail_in_category") or "policy"),
    )

    return {
        "session_id": session_id,
        "trace_id": trace_id,
        "node_latencies_ms": lat,
        "total_latency_ms": total_ms,
    }


def _build_compiled_graph():
    if not HAS_LANGGRAPH or StateGraph is None:
        return None
    builder = StateGraph(AgentGraphState)
    builder.add_node("perceive", _node_perceive)
    builder.add_node("guardrail_in", _node_guardrail_in)
    builder.add_node("finalize_blocked", _node_finalize_blocked)
    builder.add_node("retrieve_rag", _node_retrieve_rag)
    builder.add_node("plan_and_tools", _node_plan_and_tools)
    builder.add_node("reason_llm", _node_reason_llm)
    builder.add_node("guardrail_out", _node_guardrail_out)
    builder.add_node("persist_and_trace", _node_persist_and_trace)

    builder.set_entry_point("perceive")
    builder.add_edge("perceive", "guardrail_in")
    builder.add_conditional_edges(
        "guardrail_in",
        _route_after_guardrail_in,
        {"blocked": "finalize_blocked", "allowed": "retrieve_rag"},
    )
    builder.add_edge("finalize_blocked", "persist_and_trace")
    builder.add_edge("retrieve_rag", "plan_and_tools")
    builder.add_edge("plan_and_tools", "reason_llm")
    builder.add_edge("reason_llm", "guardrail_out")
    builder.add_edge("guardrail_out", "persist_and_trace")
    builder.add_edge("persist_and_trace", END)
    return builder.compile()


class AgentGraphService:
    """Orquestador principal del módulo agéntico IA de AeroGuard."""

    def __init__(self):
        self._graph = _build_compiled_graph()

    async def run_query(
        self,
        *,
        query: str,
        user_id: str,
        username: str,
        user_role: str,
        session_id: Optional[str] = None,
        telemetry: Optional[Mapping[str, Any]] = None,
        zone: Optional[Mapping[str, Any]] = None,
        dispatch_event: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, Any]:
        initial_state: AgentGraphState = {
            "query": query,
            "session_id": session_id,
            "user_id": user_id,
            "username": username,
            "user_role": user_role,
            "telemetry": dict(telemetry) if telemetry else None,
            "zone": dict(zone) if zone else None,
            "dispatch_event": bool(dispatch_event),
            "node_latencies_ms": {},
        }
        cfg: RunnableConfig = {"configurable": {"db": db}}

        if self._graph is not None:
            final_state: AgentGraphState = await self._graph.ainvoke(initial_state, config=cfg)
            engine_name = "langgraph"
        else:
            # Fallback secuencial idéntico solo si langgraph no está instalado en el contenedor
            s = dict(initial_state)
            s.update(await _node_perceive(s, cfg))
            s.update(await _node_guardrail_in(s, cfg))
            if _route_after_guardrail_in(s) == "blocked":
                s.update(await _node_finalize_blocked(s, cfg))
            else:
                s.update(await _node_retrieve_rag(s, cfg))
                s.update(await _node_plan_and_tools(s, cfg))
                s.update(await _node_reason_llm(s, cfg))
                s.update(await _node_guardrail_out(s, cfg))
            s.update(await _node_persist_and_trace(s, cfg))
            final_state = s  # type: ignore[assignment]
            engine_name = "sequential_fallback"

        return {
            "session_id": final_state.get("session_id"),
            "trace_id": final_state.get("trace_id"),
            "status": final_state.get("status"),
            "engine": engine_name,
            "provider": final_state.get("provider"),
            "vector_backend": final_state.get("vector_backend") or agent_rag_service.status()["vector_backend"],
            "output": final_state.get("final_output"),
            "guardrails": {
                "input_passed": final_state.get("guardrail_in_passed"),
                "input_category": final_state.get("guardrail_in_category"),
                "input_reason": final_state.get("guardrail_in_reason"),
                "output_passed": final_state.get("guardrail_out_passed"),
                "output_reason": final_state.get("guardrail_out_reason"),
            },
            "rag_citations": final_state.get("rag_citations") or [],
            "tools_called": final_state.get("tools_called") or [],
            "tool_outputs": final_state.get("tool_outputs") or {},
            "telemetry_trace": {
                "node_latencies_ms": final_state.get("node_latencies_ms") or {},
                "total_latency_ms": final_state.get("total_latency_ms") or 0.0,
                "estimated_tokens": final_state.get("estimated_tokens") or 0,
            },
        }


agent_graph_service = AgentGraphService()
