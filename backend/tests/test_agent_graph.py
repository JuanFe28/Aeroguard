"""Pruebas integradas del grafo LangGraph, Qdrant RAG embebido, herramientas, memoria, MCP y LLMOps."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.services.agent_rag_service import agent_rag_service

ADMIN_AUTH = {"Authorization": "Bearer " + create_access_token({"sub": "admin", "role": "admin"})}
ANALYST_AUTH = {"Authorization": "Bearer " + create_access_token({"sub": "analista", "role": "analyst"})}


@pytest.fixture(autouse=True)
def isolated_qdrant_memory():
    agent_rag_service.reset_client(":memory:")
    yield
    agent_rag_service.reset_client(None)


def test_agent_rag_embedded_qdrant_reindex_and_search():
    reindex = agent_rag_service.reindex_corpus()
    assert reindex["indexed_chunks"] >= 4
    assert reindex["vector_backend"] == "qdrant_embedded"

    hits = agent_rag_service.search("cota 120 metros jamming protocolo defensivo", top_k=3)
    assert len(hits) >= 1
    assert any("01_protocolos_operativos_cuas.md" in h["source"] for h in hits)


def test_agent_langgraph_query_tools_rag_memory_and_traces(isolated_client: TestClient):
    res = isolated_client.post(
        "/api/v1/agent/query",
        json={
            "query": "Evalúa el contacto y el pronóstico ARIMA de picos según las reglas de geocercas de Bucaramanga",
            "telemetry": {
                "drone_id": "UAV-LG-01",
                "altitude_m": 155.0,
                "speed_ms": 24.0,
                "distance_to_zone_m": 85.0,
                "rf_signal_dbm": -42.0,
                "ai_confidence": 0.92,
                "drone_class": "diy_custom",
                "flight_pattern": "Evasivo",
            },
            "zone": {"name": "Aeropuerto Palonegro", "max_allowed_altitude_m": 120.0},
            "dispatch_event": False,
        },
        headers=ADMIN_AUTH,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["engine"] == "langgraph"
    assert data["vector_backend"] == "qdrant_embedded"
    assert data["status"] == "completed"
    assert data["guardrails"]["input_passed"] is True
    assert data["guardrails"]["output_passed"] is True
    assert len(data["rag_citations"]) >= 1
    for tool_name in ("get_operational_snapshot", "evaluate_goal_agent", "predict_telemetry_ml", "get_incursion_forecast"):
        assert tool_name in data["tools_called"]
    assert data["output"]["human_review_required"] is True
    assert data["output"]["priority"] in {"HIGH", "CRITICAL"}
    assert data["telemetry_trace"]["total_latency_ms"] >= 0.0

    # Verificar memoria persistente de la sesión (segundo turno en la misma sesión)
    session_id = data["session_id"]
    follow_up = isolated_client.post(
        "/api/v1/agent/query",
        json={
            "query": "Confirma las citas del protocolo de revisión humana",
            "session_id": session_id,
        },
        headers=ADMIN_AUTH,
    )
    assert follow_up.status_code == 200
    assert follow_up.json()["data"]["session_id"] == session_id

    sess_detail = isolated_client.get(f"/api/v1/agent/sessions/{session_id}", headers=ADMIN_AUTH)
    assert sess_detail.status_code == 200
    assert len(sess_detail.json()["data"]["messages"]) == 4

    # Verificar que analista no puede leer sesiones privadas de admin
    forbidden = isolated_client.get(f"/api/v1/agent/sessions/{session_id}", headers=ANALYST_AUTH)
    assert forbidden.status_code == 403

    # Verificar trazas LLMOps y /metrics
    llmops = isolated_client.get("/api/v1/agent/llmops/summary", headers=ADMIN_AUTH)
    assert llmops.status_code == 200
    assert llmops.json()["data"]["total_runs"] >= 2
    assert llmops.json()["data"]["rag_status"]["vector_backend"] == "qdrant_embedded"

    metrics_res = isolated_client.get("/metrics", headers=ADMIN_AUTH)
    assert metrics_res.status_code == 200
    assert "aeroguard_agent_requests_total" in metrics_res.text


def test_agent_mcp_jsonrpc_endpoints(isolated_client: TestClient):
    listed = isolated_client.post(
        "/api/v1/agent/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        headers=ANALYST_AUTH,
    )
    assert listed.status_code == 200
    names = [t["name"] for t in listed.json()["result"]["tools"]]
    assert {"search_cuas_knowledge", "evaluate_goal_agent", "predict_telemetry_ml", "get_incursion_forecast"}.issubset(names)

    called = isolated_client.post(
        "/api/v1/agent/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "predict_telemetry_ml",
                "arguments": {"altitude_m": 150.0, "speed_ms": 22.0, "distance_to_zone_m": 90.0},
            },
        },
        headers=ANALYST_AUTH,
    )
    assert called.status_code == 200
    payload = called.json()["result"]["content"][0]["json"]
    assert payload["threat_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
