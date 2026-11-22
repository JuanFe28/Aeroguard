"""
AeroGuard — Predictive Analytics Endpoints (CRISP-DM 6 Modelos)

Expone la analítica predictiva liviana sin alterar la tabla de alertas ni
el dictamen táctico operativo vigente:
- GET  /api/v1/predictions/summary   -> Comparativa de los 6 modelos y decisión productiva
- GET  /api/v1/predictions/forecast  -> Pronóstico diario ARIMA a 14 días
- POST /api/v1/predictions/evaluate  -> Evaluación multi-modelo sobre telemetría
"""

import json
from typing import Callable, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from app.core.security import require_permission
from app.services.predictive_ml_service import predictive_ml_service


class StrictJsonRoute(APIRoute):
    """Rechaza literales JSON no finitos (NaN/Infinity) con HTTP 422 limpio."""

    def get_route_handler(self) -> Callable[[Request], Response]:
        original_handler = super().get_route_handler()

        async def custom_handler(request: Request) -> Response:
            if request.method in {"POST", "PUT", "PATCH"}:
                raw_body = await request.body()
                if raw_body:
                    def _reject_non_finite(token: str):
                        raise ValueError(f"Literal no finito no permitido en JSON: {token}")

                    try:
                        json.loads(raw_body.decode("utf-8"), parse_constant=_reject_non_finite)
                    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                        return JSONResponse(status_code=422, content={"detail": str(exc)})
            return await original_handler(request)

        return custom_handler


router = APIRouter(route_class=StrictJsonRoute)


class TelemetryPredictionRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    drone_id: Optional[str] = Field(default="UAV-SIM-01", min_length=1, max_length=64)
    altitude_m: float = Field(ge=0.0, le=1500.0)
    speed_ms: float = Field(ge=0.0, le=100.0)
    vertical_speed_ms: float = Field(default=0.0, ge=-30.0, le=30.0)
    heading_deg: float = Field(default=180.0, ge=0.0, le=360.0)
    distance_to_zone_m: float = Field(ge=0.0, le=25000.0)
    rf_signal_dbm: float = Field(default=-72.0, ge=-130.0, le=-10.0)
    battery_est_pct: float = Field(default=75.0, ge=0.0, le=100.0)
    ai_confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    wind_speed_kmh: float = Field(default=12.0, ge=0.0, le=120.0)
    drone_class: Literal["quadcopter", "fixed_wing", "hexacopter", "diy_custom", "bird_false_pos"] = "quadcopter"
    flight_pattern: Literal["Directo", "Erratico", "Estacionario", "Patrullaje", "Evasivo"] = "Directo"
    weather_condition: Literal["Despejado", "Nublado", "Lluvia", "Niebla"] = "Despejado"
    city_zone: Literal["Bucaramanga", "Bogota"] = "Bucaramanga"


@router.get("/summary", summary="Resumen comparativo de los 6 modelos CRISP-DM")
async def get_predictive_summary(current_user=Depends(require_permission("alerts:read"))):
    """Devuelve métricas comparativas de los 6 modelos evaluados y el modelo en producción."""
    try:
        return {"status": "success", "data": predictive_ml_service.get_models_summary()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/forecast", summary="Pronóstico diario ARIMA de incursiones de alto riesgo")
async def get_incursion_forecast(current_user=Depends(require_permission("alerts:read"))):
    """Devuelve la serie reciente y el pronóstico ARIMA a 14 días con intervalos al 95 %."""
    try:
        return {"status": "success", "data": predictive_ml_service.get_forecast()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/evaluate", summary="Evaluar telemetría con modelos predictivos CRISP-DM")
async def evaluate_telemetry_ml(
    body: TelemetryPredictionRequest,
    current_user=Depends(require_permission("alerts:read")),
):
    """Ejecuta Random Forest, Regresión Lineal, Regresión Logística y K-Means sin efectos laterales."""
    try:
        prediction = predictive_ml_service.evaluate_telemetry(body.model_dump())
        return {
            "status": "success",
            "simulation": True,
            "drone_id": body.drone_id,
            "data": prediction,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
