"""
AeroGuard — Endpoints del Agente IA (LangGraph + RAG Qdrant + Guardrails + LLMOps + MCP)
"""

from __future__ import annotations

from typing import Any, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_permission
from app.core.validation import StrictJsonRoute, UUIDText, valid_uuid
from app.models.models import AgentMessage, AgentSession, AgentTrace
from app.services.agent_graph_service import agent_graph_service
from app.services.agent_llmops import get_llmops_summary
from app.services.agent_rag_service import agent_rag_service
from app.services.mcp_server import handle_mcp_jsonrpc

router = APIRouter(route_class=StrictJsonRoute)


class AgentTelemetryContext(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    drone_id: str = Field(default="UAV-QUERY-01", min_length=1, max_length=64)
    altitude_m: float = Field(ge=0.0, le=1500.0)
    speed_ms: float = Field(ge=0.0, le=100.0)
    distance_to_zone_m: float = Field(default=250.0, ge=0.0, le=25000.0)
    rf_signal_dbm: float = Field(default=-72.0, ge=-130.0, le=-10.0)
    ai_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    drone_class: Literal["quadcopter", "fixed_wing", "hexacopter", "diy_custom", "bird_false_pos"] = "quadcopter"
    flight_pattern: Literal["Directo", "Erratico", "Estacionario", "Patrullaje", "Evasivo"] = "Directo"


class AgentZoneContext(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    name: str = Field(default="Zona Operativa", min_length=1, max_length=128)
    max_allowed_altitude_m: float = Field(default=120.0, ge=0.0, le=15000.0)


class AgentQuerySchema(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    query: str = Field(min_length=1, max_length=4000)
    session_id: Optional[UUIDText] = None
    telemetry: Optional[AgentTelemetryContext] = None
    zone: Optional[AgentZoneContext] = None
    dispatch_event: bool = False


class McpRpcSchema(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    jsonrpc: str = "2.0"
    id: Optional[Any] = 1
    method: str = Field(min_length=1, max_length=128)
    params: dict[str, Any] = Field(default_factory=dict)


@router.post("/query", summary="Consultar al agente IA LangGraph con RAG, herramientas y guardrails")
async def query_agent(
    body: AgentQuerySchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("alerts:read")),
):
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    result = await agent_graph_service.run_query(
        query=body.query,
        session_id=body.session_id,
        user_id=str(getattr(current_user, "id", current_user.username)),
        username=current_user.username,
        user_role=role_val,
        telemetry=body.telemetry.model_dump() if body.telemetry else None,
        zone=body.zone.model_dump() if body.zone else None,
        dispatch_event=body.dispatch_event,
        db=db,
    )
    return {"status": "success", "data": result}


@router.get("/sessions", summary="Listar sesiones de memoria del agente IA")
async def list_agent_sessions(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("alerts:read")),
):
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    q = select(AgentSession).order_by(desc(AgentSession.updated_at)).limit(limit)
    if role_val != "admin":
        q = q.where(AgentSession.user_id == str(getattr(current_user, "id", current_user.username)))
    rows = (await db.execute(q)).scalars().all()
    return {
        "status": "success",
        "data": [
            {
                "id": s.id,
                "username": s.username,
                "role": s.role,
                "title": s.title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in rows
        ],
    }


@router.get("/sessions/{session_id}", summary="Consultar mensajes persistidos de una sesión agéntica")
async def get_agent_session_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("alerts:read")),
):
    sid = valid_uuid(session_id)
    sess = await db.get(AgentSession, sid)
    if sess is None:
        raise HTTPException(status_code=404, detail="Sesión agéntica no encontrada.")
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_val != "admin" and sess.user_id != str(getattr(current_user, "id", current_user.username)):
        raise HTTPException(status_code=403, detail="No autorizado para consultar la sesión de otro usuario.")

    msgs = (
        await db.execute(
            select(AgentMessage).where(AgentMessage.session_id == sid).order_by(AgentMessage.created_at)
        )
    ).scalars().all()
    return {
        "status": "success",
        "data": {
            "id": sess.id,
            "username": sess.username,
            "role": sess.role,
            "title": sess.title,
            "messages": [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "content": m.content,
                    "metadata": m.metadata_json,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in msgs
            ],
        },
    }


@router.get("/traces", summary="Listar trazas recientes LLMOps")
async def list_agent_traces(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("alerts:read")),
):
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    q = select(AgentTrace).order_by(desc(AgentTrace.created_at)).limit(limit)
    if role_val != "admin":
        q = q.where(AgentTrace.username == current_user.username)
    rows = (await db.execute(q)).scalars().all()
    return {
        "status": "success",
        "data": [
            {
                "id": t.id,
                "session_id": t.session_id,
                "username": t.username,
                "role": t.role,
                "provider": t.provider,
                "engine": t.engine,
                "guardrail_in_passed": t.guardrail_in_passed,
                "guardrail_out_passed": t.guardrail_out_passed,
                "blocked_reason": t.blocked_reason,
                "rag_hits": t.rag_hits,
                "tools_called": t.tools_called,
                "node_latencies_ms": t.node_latencies_ms,
                "total_latency_ms": t.total_latency_ms,
                "estimated_tokens": t.estimated_tokens,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in rows
        ],
    }


@router.get("/llmops/summary", summary="Resumen de observabilidad LLMOps y estado RAG Qdrant")
async def agent_llmops_summary(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("alerts:read")),
):
    summary = await get_llmops_summary(db)
    summary["rag_status"] = agent_rag_service.status()
    return {"status": "success", "data": summary}


@router.post("/rag/reindex", summary="Re-indexar manualmente el corpus C-UAS en Qdrant")
async def reindex_rag_corpus(current_user=Depends(require_permission("config:write"))):
    info = agent_rag_service.reindex_corpus()
    return {"status": "success", "data": info}


@router.post("/mcp", summary="Adaptador JSON-RPC 2.0 MCP de herramientas AeroGuard")
async def mcp_rpc_endpoint(
    body: McpRpcSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("alerts:read")),
):
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    return await handle_mcp_jsonrpc(body.model_dump(), user_role=role_val, db=db)
