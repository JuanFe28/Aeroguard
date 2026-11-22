"""
AeroGuard — Adaptador MCP (Model Context Protocol) Liviano vía JSON-RPC 2.0

Expone las herramientas de AeroGuard y la búsqueda RAG en Qdrant bajo un contrato
estructurado compatible con clientes MCP sin levantar un contenedor adicional.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import has_permission
from app.services.agent_rag_service import agent_rag_service
from app.services.agent_tools import (
    run_forecast_tool,
    run_goal_agent_tool,
    run_operational_snapshot_tool,
    run_predictive_ml_tool,
)

MCP_PROTOCOL_VERSION = "2024-11-05"

MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_cuas_knowledge",
        "description": "Busca protocolos C-UAS, reglas de geocercas y conocimiento CRISP-DM en Qdrant.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "evaluate_goal_agent",
        "description": "Evalúa telemetría con el motor determinista basado en objetivos.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "drone": {"type": "object"},
                "zone": {"type": "object"},
            },
            "required": ["drone", "zone"],
        },
    },
    {
        "name": "predict_telemetry_ml",
        "description": "Ejecuta Random Forest, Regresión Lineal/Logística y K-Means sobre telemetría.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "altitude_m": {"type": "number"},
                "speed_ms": {"type": "number"},
                "distance_to_zone_m": {"type": "number"},
                "drone_class": {"type": "string"},
                "flight_pattern": {"type": "string"},
            },
            "required": ["altitude_m", "speed_ms", "distance_to_zone_m"],
        },
    },
    {
        "name": "get_incursion_forecast",
        "description": "Devuelve el pronóstico temporal ARIMA(1,1,1) de incursiones a 14 días.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_operational_snapshot",
        "description": "Obtiene resumen de zonas activas, sensores y alertas según permisos RBAC.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def list_mcp_tools() -> list[dict[str, Any]]:
    return MCP_TOOLS


async def call_mcp_tool(
    name: str,
    arguments: Mapping[str, Any],
    user_role: Any,
    db: Optional[AsyncSession] = None,
) -> dict[str, Any]:
    role_val = user_role.value if hasattr(user_role, "value") else str(user_role)
    if not has_permission(role_val, "alerts:read"):
        return {"isError": True, "error": "Permiso RBAC alerts:read requerido para invocar MCP."}

    if name == "search_cuas_knowledge":
        q = str(arguments.get("query", "")).strip()
        k = int(arguments.get("top_k", 3))
        hits = agent_rag_service.search(q, top_k=k)
        return {"isError": False, "result": {"hits": hits}}

    if name == "evaluate_goal_agent":
        drone = arguments.get("drone") or {}
        zone = arguments.get("zone") or {}
        return {"isError": False, "result": run_goal_agent_tool(drone, zone)}

    if name == "predict_telemetry_ml":
        return {"isError": False, "result": run_predictive_ml_tool(arguments)}

    if name == "get_incursion_forecast":
        return {"isError": False, "result": run_forecast_tool()}

    if name == "get_operational_snapshot":
        return {"isError": False, "result": await run_operational_snapshot_tool(db, role_val)}

    return {"isError": True, "error": f"Herramienta MCP desconocida: {name}"}


async def handle_mcp_jsonrpc(
    payload: Mapping[str, Any],
    user_role: Any,
    db: Optional[AsyncSession] = None,
) -> dict[str, Any]:
    rpc_id = payload.get("id")
    method = str(payload.get("method", ""))
    params = payload.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "serverInfo": {"name": "aeroguard-mcp", "version": settings.APP_VERSION},
                "capabilities": {"tools": {"listChanged": False}},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": list_mcp_tools()}}

    if method == "tools/call":
        tool_name = str(params.get("name", ""))
        args = params.get("arguments") or {}
        outcome = await call_mcp_tool(tool_name, args, user_role=user_role, db=db)
        if outcome.get("isError"):
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {"code": -32602, "message": str(outcome.get("error", "Error MCP"))},
            }
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {"content": [{"type": "json", "json": outcome["result"]}]},
        }

    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "error": {"code": -32601, "message": f"Método MCP no soportado: {method}"},
    }
