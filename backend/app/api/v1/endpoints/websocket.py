"""
AeroGuard — WebSocket Endpoint
Comunicación en tiempo real: detecciones, alertas, sensores, telemetría y heartbeat táctico.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState
from typing import Dict, Set, List, Tuple, Optional
import asyncio
import json
from datetime import datetime, timezone

from app.core.security import get_current_user

router = APIRouter()


# ============================================================
# Connection Manager (Soporta múltiples sesiones y heartbeat)
# ============================================================

class ConnectionManager:
    def __init__(self):
        # user_id -> Set[WebSocket]
        self._active: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self._lock:
            if user_id not in self._active:
                self._active[user_id] = set()
            self._active[user_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: str):
        async with self._lock:
            if user_id in self._active:
                self._active[user_id].discard(websocket)
                if not self._active[user_id]:
                    self._active.pop(user_id, None)

    async def send_to(self, user_id: str, message: dict):
        payload = json.dumps(message, default=str)
        async with self._lock:
            sockets = list(self._active.get(user_id, set()))
        for ws in sockets:
            if ws.client_state == WebSocketState.CONNECTED:
                try:
                    await ws.send_text(payload)
                except Exception:
                    await self.disconnect(ws, user_id)

    async def broadcast(self, message: dict, role_filter: Optional[str] = None):
        """Broadcast a todos los operadores conectados."""
        payload = json.dumps(message, default=str)
        disconnected: List[Tuple[WebSocket, str]] = []
        async with self._lock:
            targets = [(uid, ws) for uid, ws_set in self._active.items() for ws in ws_set]

        for user_id, ws in targets:
            if ws.client_state == WebSocketState.CONNECTED:
                try:
                    await ws.send_text(payload)
                except Exception:
                    disconnected.append((ws, user_id))

        for ws, uid in disconnected:
            await self.disconnect(ws, uid)

    @property
    def active_count(self) -> int:
        return sum(len(ws_set) for ws_set in self._active.values())


manager = ConnectionManager()


# ============================================================
# WebSocket Endpoint con Heartbeat Activo y Resiliencia
# ============================================================

@router.websocket("/live")
async def websocket_live(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint para actualizaciones en tiempo real.
    - Requiere JWT o demo token como query param: ws://host/ws/live?token=<jwt>
    - Envía: detecciones nuevas, alertas, estado de sensores, dictámenes IA
    - Heartbeat activo con ping/pong bidireccional y métricas de latencia RTT.
    """
    # Validar JWT o token de demostración
    try:
        current_user = await get_current_user(token)
        user_id = current_user.username
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Se requiere un token de acceso con usuario válido")
    except Exception:
        await websocket.close(code=4001, reason="Token inválido o expirado")
        return

    await manager.connect(websocket, user_id)
    try:
        # Enviar mensaje de bienvenida y configuración de cadencia de heartbeat
        await websocket.send_json({
            "type": "connected",
            "data": {
                "message": "Conexión táctica establecida con éxito",
                "user": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_connections": manager.active_count,
                "heartbeat_interval_s": 15,
                "heartbeat_timeout_s": 7,
            }
        })

        # Loop de escucha de mensajes cliente (ping/pong, suscripciones, etc.)
        while True:
            try:
                raw_text = await asyncio.wait_for(websocket.receive_text(), timeout=25.0)
                try:
                    data = json.loads(raw_text)
                except Exception:
                    data = {"type": raw_text.strip().lower()}

                msg_type = data.get("type")
                if msg_type == "ping":
                    # Responder de inmediato con pong y timestamp para cálculo de RTT
                    client_ts = data.get("data", {}).get("timestamp") if isinstance(data.get("data"), dict) else None
                    await websocket.send_json({
                        "type": "pong",
                        "data": {
                            "client_timestamp": client_ts,
                            "server_timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    })
                elif msg_type == "pong":
                    # Cliente confirmó respuesta de vida
                    pass

            except asyncio.TimeoutError:
                # Si el cliente estuvo en silencio por 25s, enviar ping de prueba de vida
                try:
                    await websocket.send_json({
                        "type": "ping",
                        "data": {
                            "server_timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    })
                except Exception:
                    break
            except WebSocketDisconnect:
                break
            except Exception:
                break

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, user_id)


# ============================================================
# Helpers de Broadcast
# ============================================================

async def broadcast_detection(detection_data: dict):
    """Retransmite una nueva detección a todos los clientes conectados."""
    await manager.broadcast({
        "type": "detection_new",
        "data": detection_data,
    })


async def broadcast_alert(alert_data: dict):
    """Retransmite una nueva alerta a todos los clientes conectados."""
    await manager.broadcast({
        "type": "alert_new",
        "data": alert_data,
    })


async def broadcast_sensor_update(sensor_data: dict):
    """Retransmite cambio de estado de sensores."""
    await manager.broadcast({
        "type": "sensor_update",
        "data": sensor_data,
    })
