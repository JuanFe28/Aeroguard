"""
AeroGuard — Herramientas Verificables del Agente IA

Conecta el grafo LangGraph (y el servidor MCP) con capacidades reales del sistema:
- goal_based_agent.py (motor determinista basado en objetivos del compañero)
- predictive_ml_service.py (Random Forest, Regresión Lineal/Logística, K-Means, ARIMA)
- Base de datos operativa (zonas restringidas, sensores y alertas abiertas)
- Despacho opcional SOAR / WebSocket / n8n via ai_tactical_agent_service.py
"""

from __future__ import annotations

from typing import Any, Mapping, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import has_permission
from app.models.models import Alert, AlertStatus, RestrictedZone, Sensor, SensorStatus
from app.services.ai_tactical_agent_service import ai_tactical_service
from app.services.goal_based_agent import evaluate_goals
from app.services.predictive_ml_service import predictive_ml_service


def run_goal_agent_tool(drone: Mapping[str, Any], zone: Mapping[str, Any]) -> dict[str, Any]:
    """Ejecuta el motor basado en objetivos sin modificar ni romper su contrato."""
    decision = evaluate_goals(drone, zone)
    return decision.to_dict()


def run_predictive_ml_tool(telemetry: Mapping[str, Any]) -> dict[str, Any]:
    """Ejecuta Random Forest + Regresión Lineal + Regresión Logística + K-Means."""
    return predictive_ml_service.evaluate_telemetry(telemetry)


def run_forecast_tool() -> dict[str, Any]:
    """Consulta el pronóstico ARIMA(1,1,1) de incursiones diarias a 14 días."""
    fc = predictive_ml_service.get_forecast()
    return {
        "model": fc["model"],
        "peak_forecast_14d": fc["peak_forecast_14d"],
        "metrics": {
            "mae": fc["metrics"].get("test_mae"),
            "rmse": fc["metrics"].get("test_rmse"),
            "mape_pct": fc["metrics"].get("test_mape_pct"),
            "aic": fc["metrics"].get("aic"),
        },
    }


async def run_operational_snapshot_tool(
    db: Optional[AsyncSession],
    user_role: Any,
) -> dict[str, Any]:
    """Consulta el estado operativo en BD respetando permisos RBAC del operador."""
    if db is None:
        return {"available": False, "reason": "Sin sesión de base de datos."}

    role_val = user_role.value if hasattr(user_role, "value") else str(user_role)
    snapshot: dict[str, Any] = {"available": True, "role": role_val}

    if has_permission(role_val, "zones:read"):
        zone_rows = (
            await db.execute(
                select(RestrictedZone.name, RestrictedZone.max_altitude, RestrictedZone.threat_level)
                .where(RestrictedZone.is_active.is_(True))
                .limit(10)
            )
        ).all()
        snapshot["active_zones_count"] = len(zone_rows)
        snapshot["active_zones"] = [
            {
                "name": z.name,
                "max_altitude_m": float(z.max_altitude or 0.0),
                "threat_level": z.threat_level.value if hasattr(z.threat_level, "value") else str(z.threat_level),
            }
            for z in zone_rows
        ]

    if has_permission(role_val, "alerts:read"):
        open_alerts = (
            await db.execute(
                select(func.count()).select_from(Alert).where(Alert.status == AlertStatus.OPEN)
            )
        ).scalar_one()
        snapshot["open_alerts_count"] = int(open_alerts)

    if has_permission(role_val, "sensors:read"):
        active_sensors = (
            await db.execute(
                select(func.count()).select_from(Sensor).where(Sensor.status == SensorStatus.ACTIVE)
            )
        ).scalar_one()
        snapshot["active_sensors_count"] = int(active_sensors)

    return snapshot


async def run_dispatch_soar_tool(
    payload: Mapping[str, Any],
    user_role: Any,
) -> dict[str, Any]:
    """Despacha evento táctico hacia ai_tactical_service (n8n/WebSocket) bajo permiso alerts:write."""
    role_val = user_role.value if hasattr(user_role, "value") else str(user_role)
    if not has_permission(role_val, "alerts:write"):
        return {
            "dispatched": False,
            "reason": f"Permiso 'alerts:write' requerido para despachar SOAR (rol '{role_val}').",
        }

    result = await ai_tactical_service.analyze_incident(dict(payload))
    return {
        "dispatched": True,
        "incident_id": result.get("incident_id"),
        "execution_source": result.get("execution_source"),
        "threat_level": result.get("threat_level"),
        "dispatched_to_n8n": result.get("dispatched_to_n8n"),
    }
