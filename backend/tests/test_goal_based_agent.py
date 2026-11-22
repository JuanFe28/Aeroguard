"""Pruebas sin dependencias externas del modelo basado en objetivos."""
from app.services.goal_based_agent import evaluate_goals


def test_exceeds_altitude_threshold_proposes_review():
    d = evaluate_goals({"altitude_m": 135, "speed_ms": 12, "ai_confidence": .92},
                       {"max_allowed_altitude_m": 120})
    assert d.action == "NOTIFICAR_Y_VERIFICAR"
    assert d.priority == "CRITICAL"
    assert d.human_review_required
    assert "135" in d.evidence[0]


def test_below_threshold_is_monitored():
    d = evaluate_goals({"altitude_m": 95}, {"max_allowed_altitude_m": 120})
    assert d.action == "MONITOREAR"
    assert d.priority == "NORMAL"


def test_low_confidence_requires_verification_not_critical_alarm():
    d = evaluate_goals({"altitude_m": 150, "ai_confidence": .25},
                       {"max_allowed_altitude_m": 120})
    assert d.action == "VERIFICAR_DETECCION"
    assert d.priority == "REVIEW"


def test_missing_or_invalid_sensor_values_are_indeterminate():
    for data in ({}, {"altitude_m": "nan"}, {"altitude_m": -9}):
        d = evaluate_goals(data, {"max_allowed_altitude_m": 120})
        assert d.action == "SOLICITAR_DATOS"
        assert d.priority == "INDETERMINATE"


def test_decision_has_trace_and_goals():
    decision = evaluate_goals({"altitude_m": 151}, {"max_allowed_altitude_m": 120})
    record = decision.to_dict()
    assert record["goals"] and record["evidence"] and record["explanation"]
    assert record["model"] == "basado_en_objetivos"
