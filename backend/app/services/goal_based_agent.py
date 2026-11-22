"""Agente basado en objetivos para evaluación defensiva de incidentes.

El módulo es determinista, no clasifica imágenes ni atribuye intenciones.
Solo recomienda acciones informativas que requieren revisión humana.
"""

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any, Mapping

GOALS = (
    "Mantener vigilancia de los eventos reportados",
    "Priorizar la revisión de eventos sobre umbrales configurados",
    "Evitar alarmas críticas sin evidencia suficiente",
    "Conservar una justificación verificable de cada decisión",
)


@dataclass(frozen=True)
class GoalDecision:
    model: str
    goals: tuple[str, ...]
    action: str
    priority: str
    evidence: tuple[str, ...]
    explanation: str
    human_review_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["goals"] = list(self.goals)
        result["evidence"] = list(self.evidence)
        return result


def _number(mapping: Mapping[str, Any], field: str) -> float | None:
    try:
        value = mapping.get(field)
        if value is None or isinstance(value, bool):
            return None
        numeric = float(value)
        return numeric if isfinite(numeric) else None
    except (TypeError, ValueError):
        return None


def evaluate_goals(drone: Mapping[str, Any], zone: Mapping[str, Any]) -> GoalDecision:
    """Percepción -> evaluación de metas -> decisión explicable -> recomendación.

    Un umbral de altitud no demuestra por sí mismo invasión de geocerca ni
    autoriza conclusiones sobre intención o identidad del objeto.
    """
    altitude = _number(drone, "altitude_m")
    ceiling = _number(zone, "max_allowed_altitude_m")
    speed = _number(drone, "speed_ms")
    confidence = _number(drone, "ai_confidence")
    evidence: list[str] = []

    if altitude is None or ceiling is None or altitude < 0 or ceiling < 0:
        evidence.append("Altitud o umbral no disponible/incorrecto")
        return GoalDecision(
            "basado_en_objetivos", GOALS, "SOLICITAR_DATOS", "INDETERMINATE",
            tuple(evidence), "No es posible evaluar el objetivo de vigilancia sin telemetría válida.",
        )

    exceeded = altitude > ceiling
    evidence.append(f"Altitud observada: {altitude:g} m; umbral: {ceiling:g} m")
    if speed is not None and speed >= 0:
        evidence.append(f"Velocidad observada: {speed:g} m/s")
    if confidence is not None and 0 <= confidence <= 1:
        evidence.append(f"Confianza del análisis visual: {confidence:.2f} (no calibrada)")

    if exceeded:
        evidence.append("Se superó el umbral de altitud configurado")
        if confidence is not None and 0 <= confidence < 0.5:
            return GoalDecision(
                "basado_en_objetivos", GOALS, "VERIFICAR_DETECCION", "REVIEW",
                tuple(evidence), "Priorizar verificación humana: la confianza visual declarada es baja.",
            )
        return GoalDecision(
            "basado_en_objetivos", GOALS, "NOTIFICAR_Y_VERIFICAR", "CRITICAL",
            tuple(evidence), "Solicitar revisión humana del evento y notificar al responsable; no se infiere intención.",
        )

    evidence.append("No se superó el umbral de altitud configurado")
    return GoalDecision(
        "basado_en_objetivos", GOALS, "MONITOREAR", "NORMAL",
        tuple(evidence), "Mantener seguimiento; este criterio no confirma seguridad ni autorización.",
    )
