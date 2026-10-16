"""
AeroGuard — AI Tactical Agent Service (SOAR & Threat Analysis)
Implementa el razonamiento táctico militar C-UAS y el webhook de incidentes hacia n8n
con fallback autónomo embebido.
"""

import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class AITacticalAgentService:
    """
    Servicio de Inteligencia Artificial Táctico para respuesta a incidentes (SOAR).
    Dispara eventos hacia el webhook de n8n y, si n8n no está disponible, ejecuta
    la evaluación cinemática y de amenaza localmente respetando los protocolos C-UAS.
    """

    def __init__(self):
        self.webhook_url = settings.N8N_WEBHOOK_URL
        self.timeout = settings.N8N_WEBHOOK_TIMEOUT

    async def analyze_incident(self, incident_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa una intrusión de dron en zona restringida.
        1. Intenta enviar el payload al webhook de n8n para análisis SOAR.
        2. Si n8n está fuera de línea, genera el dictamen mediante el motor táctico local.
        3. Actualiza el estado del sistema y emite el evento en vivo vía WebSocket.
        """
        incident_id = incident_payload.get("incident_id", f"INC-{datetime.now().strftime('%Y%m%d-%H%M')}")
        drone_data = incident_payload.get("drone", {})
        zone_data = incident_payload.get("zone", {})

        drone_id = drone_data.get("drone_id", "UAV-HK-402")
        dispatched_to_n8n = False
        execution_source = "embedded_tactical_ai_engine"
        ai_verdict = ""
        threat_level = "CRITICAL"

        # 1. Intentar orquestación con n8n Webhook
        if settings.SOAR_AI_AGENT_ENABLED:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(self.webhook_url, json=incident_payload)
                    if response.status_code == 200:
                        res_json = response.json()
                        ai_verdict = res_json.get("ai_verdict") or res_json.get("output") or ""
                        threat_level = res_json.get("threat_level", "CRITICAL")
                        dispatched_to_n8n = True
                        execution_source = "n8n_soar_pipeline"
                        logger.info("Dictamen obtenido exitosamente desde n8n SOAR", incident_id=incident_id)
            except Exception as exc:
                logger.warning(
                    "n8n webhook no disponible o excedió timeout. Activando motor táctico IA embebido.",
                    error=str(exc)
                )

        # 2. Fallback: Generación determinística con el Agente IA Embebido
        if not ai_verdict:
            ai_verdict, threat_level = self._generate_embedded_tactical_verdict(drone_data, zone_data)
            execution_source = "embedded_tactical_ai_engine"

        result = {
            "incident_id": incident_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ai_verdict": ai_verdict,
            "threat_level": threat_level,
            "drone_id": drone_id,
            "dispatched_to_n8n": dispatched_to_n8n,
            "execution_source": execution_source,
            "drone": drone_data,
            "zone": zone_data,
        }

        # 3. Actualizar memoria de dictamen y retransmitir vía WebSocket
        await self._sync_and_broadcast(result)

        return result

    def _generate_embedded_tactical_verdict(
        self, drone: Dict[str, Any], zone: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        Genera el dictamen táctico con tono militar profesional según las reglas de la sección 4.2:
        1. Vector de amenaza (altitud vs techo de zona, velocidad).
        2. Hipótesis de comportamiento (automatizado vs errático).
        3. Recomendación operativa inmediata (monitoreo, patrulla, inhibición RF).
        (Menos de 55 palabras, máximo 3 oraciones).
        """
        drone_id = drone.get("drone_id", "UAV-402")
        alt = float(drone.get("altitude_m", 145.0))
        speed_ms = float(drone.get("speed_ms", 19.4))
        speed_kmh = speed_ms * 3.6
        heading = float(drone.get("heading_deg", 182.0))
        zone_name = zone.get("name", "Bucaramanga Centro / Zona Crítica")
        max_allowed_alt = float(zone.get("max_allowed_altitude_m", 120.0))

        # Determinar punto cardinal
        directions = ['norte', 'noreste', 'este', 'sureste', 'sur', 'suroeste', 'oeste', 'noroeste']
        heading_dir = directions[round(heading / 45.0) % 8]

        # Evaluación de vector de amenaza
        is_ceiling_breached = alt > max_allowed_alt
        alt_diff = round(alt - max_allowed_alt)

        if is_ceiling_breached:
            vector_text = f"{drone_id} mantiene rumbo {heading_dir} a {int(alt)}m superando el techo legal de {int(max_allowed_alt)}m (+{alt_diff}m) sobre {zone_name}."
            threat_level = "CRITICAL"
        else:
            vector_text = f"{drone_id} detectado a {int(alt)}m de altitud con rumbo {heading_dir} a {speed_kmh:.1f} km/h en {zone_name}."
            threat_level = "HIGH"

        # Hipótesis de comportamiento
        if speed_ms > 15.0:
            behavior_text = f"Vector cinemático constante a {speed_kmh:.0f} km/h sugiere vuelo automatizado con perfil de penetración premeditada."
        elif speed_ms < 5.0:
            behavior_text = "Comportamiento estacionario con oscilación mínima, compatible con vigilancia o toma de coordenadas."
        else:
            behavior_text = "Cinemática de crucero regular con telemetría C2 activa."

        # Recomendación operativa inmediata
        if is_ceiling_breached:
            action_text = "Acción: Declarar alerta perimetral táctica e iniciar protocolo de inhibición RF en 2.4/5.8 GHz."
        else:
            action_text = "Acción: Alerta perimetral a patrulla de seguridad física y seguimiento visual continuo."

        full_verdict = f"{vector_text} {behavior_text} {action_text}".strip()

        return full_verdict, threat_level

    async def _sync_and_broadcast(self, verdict_data: Dict[str, Any]):
        """Actualiza el endpoint de alertas y retransmite a la consola de los operadores."""
        try:
            import app.api.v1.endpoints.alerts as alerts_ep
            alerts_ep._latest_verdict = {
                "incident_id": verdict_data["incident_id"],
                "timestamp": verdict_data["timestamp"],
                "ai_verdict": verdict_data["ai_verdict"],
                "threat_level": verdict_data["threat_level"],
                "drone_id": verdict_data["drone_id"],
            }
        except Exception:
            pass

        try:
            from app.api.v1.endpoints.websocket import manager
            await manager.broadcast({
                "type": "ai_verdict",
                "data": verdict_data
            })
        except Exception as ws_err:
            logger.debug("WebSocket broadcast skipped or no active clients", error=str(ws_err))


# Instancia única del servicio
ai_tactical_service = AITacticalAgentService()
