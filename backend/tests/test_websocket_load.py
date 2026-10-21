"""TEST-02: carga TCP real del router WebSocket, en un puerto local efímero."""

import asyncio
import json
import math
import os
from pathlib import Path
import socket
import threading
import time

from fastapi import FastAPI
import httpx
import pytest
import uvicorn
import websockets

from app.api.v1.endpoints import websocket as endpoint
from app.core.security import create_access_token


REPORT_DIR = Path(os.environ.get(
    "AEROGUARD_LOAD_REPORT_DIR",
    str(Path(__file__).resolve().parents[2] / "docs" / "evidencias" / "TEST-02"),
))
PING_ROUNDS = 50
BROADCAST_ROUNDS = 10
MAX_P95_MS = 100


@pytest.fixture(scope="module")
def load_server():
    """Aísla el gestor, conservando el router y el transporte WebSocket reales."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    app = FastAPI()
    app.include_router(endpoint.router, prefix="/ws")
    isolated_manager = endpoint.ConnectionManager()

    @app.get("/__test__/connections")
    async def connections():
        return {"active": isolated_manager.active_count}

    @app.post("/__test__/broadcast/{sequence}")
    async def broadcast(sequence: int):
        await endpoint.broadcast_detection({"sequence": sequence, "source": "TEST-02"})
        return {"sent": sequence}

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(endpoint, "manager", isolated_manager)
        thread.start()
        try:
            deadline = time.monotonic() + 15
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.started, "El servidor de carga no inició"
            yield port, results
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            listener.close()
            (REPORT_DIR / "resultados.json").write_text(
                json.dumps({
                    "transport": "TCP/WebSocket en 127.0.0.1, puerto efímero",
                    "scope": "Router y ConnectionManager reales, autenticación con SQLite temporal; servidor de exposición separado",
                    "criteria": {"max_p95_rtt_ms": MAX_P95_MS, "errors": 0, "lost_messages": 0},
                    "scenarios": results,
                }, ensure_ascii=False, indent=2), encoding="utf-8",
            )
            assert not thread.is_alive(), "El servidor de carga no se cerró"


async def run_scenario(port, client_count):
    token = create_access_token({"sub": "admin", "role": "admin"})
    socket_url = f"ws://127.0.0.1:{port}/ws/live?token={token}"
    all_ready = asyncio.Event()
    start = asyncio.Event()
    ready = 0
    latencies = []
    broadcasts_received = []

    async def worker(client_id):
        nonlocal ready
        seen = set()
        async with websockets.connect(
            socket_url, open_timeout=15, close_timeout=3, ping_interval=None, compression=None,
        ) as ws:
            welcome = json.loads(await asyncio.wait_for(ws.recv(), 5))
            assert welcome["type"] == "connected"
            ready += 1
            if ready == client_count:
                all_ready.set()
            await start.wait()

            def accept_broadcast(message):
                assert message["type"] == "detection_new"
                assert message["data"]["source"] == "TEST-02"
                sequence = message["data"]["sequence"]
                assert sequence not in seen, "Broadcast duplicado"
                seen.add(sequence)

            for sequence in range(PING_ROUNDS):
                stamp = client_id * PING_ROUNDS + sequence
                before = time.perf_counter()
                await ws.send(json.dumps({"type": "ping", "data": {"timestamp": stamp}}))
                while True:
                    message = json.loads(await asyncio.wait_for(ws.recv(), 5))
                    if message["type"] == "pong":
                        assert message["data"]["client_timestamp"] == stamp
                        latencies.append((time.perf_counter() - before) * 1000)
                        break
                    accept_broadcast(message)
                await asyncio.sleep(0.005)

            while len(seen) < BROADCAST_ROUNDS:
                accept_broadcast(json.loads(await asyncio.wait_for(ws.recv(), 5)))
            assert seen == set(range(BROADCAST_ROUNDS))
            broadcasts_received.append(len(seen))

    tasks = [asyncio.create_task(worker(index)) for index in range(client_count)]
    before = time.perf_counter()
    try:
        await asyncio.wait_for(all_ready.wait(), 20)
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=5) as client:
            response = await client.get("/__test__/connections")
            assert response.status_code == 200
            assert response.json()["active"] == client_count
            start.set()
            for sequence in range(BROADCAST_ROUNDS):
                response = await client.post(f"/__test__/broadcast/{sequence}")
                assert response.status_code == 200
                await asyncio.sleep(0.005)
            await asyncio.wait_for(asyncio.gather(*tasks), 30)
            for _ in range(50):
                response = await client.get("/__test__/connections")
                if response.json()["active"] == 0:
                    break
                await asyncio.sleep(0.02)
            assert response.json()["active"] == 0, "Quedaron conexiones sin liberar"
    finally:
        start.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    expected_pings = client_count * PING_ROUNDS
    expected_broadcasts = client_count * BROADCAST_ROUNDS
    assert len(latencies) == expected_pings
    assert sum(broadcasts_received) == expected_broadcasts
    ordered = sorted(latencies)
    p95 = ordered[math.ceil(len(ordered) * 0.95) - 1]
    return {
        "clients": client_count,
        "ping_pong_pairs": len(latencies),
        "broadcast_deliveries": sum(broadcasts_received),
        "p50_rtt_ms": round(ordered[len(ordered) // 2], 3),
        "p95_rtt_ms": round(p95, 3),
        "max_rtt_ms": round(max(latencies), 3),
        "duration_s": round(time.perf_counter() - before, 3),
        "errors": 0,
        "lost_messages": 0,
        "remaining_connections": 0,
        "passed": p95 < MAX_P95_MS,
    }


@pytest.mark.parametrize("client_count", [10, 50, 100])
def test_concurrent_websocket_ping_and_broadcast(load_server, client_count):
    port, results = load_server
    result = asyncio.run(run_scenario(port, client_count))
    results.append(result)
    print("\nTEST-02 " + json.dumps(result, ensure_ascii=False))
    assert result["passed"], f"P95 {result['p95_rtt_ms']} ms supera el objetivo local de {MAX_P95_MS} ms"
