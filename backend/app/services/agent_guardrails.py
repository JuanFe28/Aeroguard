"""
AeroGuard — Guardrails de Entrada y Salida para Agentes IA

Capa determinista + validación estricta con Pydantic v2 (equivalente liviano de
Guardrails AI para Oracle 4 GiB RAM, evitando latencia/doble llamada de NeMo Guardrails):
- Entrada: bloqueo de prompt injection, validación RBAC según rol JWT y política C-UAS.
- Salida: esquema estructurado estricto, bloqueo de acciones cinéticas ilegales o
  filtración de secretos, y verificación de grounding contra herramientas y citas RAG.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, Field, ValidationError

from app.core.security import has_permission

_INJECTION_PATTERNS = (
    re.compile(r"ignora\s+(todas\s+|las\s+|tus\s+)?instrucciones", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+|previous\s+|prior\s+)?instructions", re.IGNORECASE),
    re.compile(r"(revela|muestra|dime|print|reveal|dump)\s+(el\s+|tu\s+|the\s+)?system\s*prompt", re.IGNORECASE),
    re.compile(r"\bjailbreak\b|modo\s+dan\b|\bact\s+as\s+dan\b|bypass\s+guardrail", re.IGNORECASE),
    re.compile(r"<\s*script\b|union\s+select|drop\s+table|/etc/passwd|os\.system\s*\(", re.IGNORECASE),
)

_SECRET_SENSITIVE_PATTERNS = (
    re.compile(r"password_hash|secret_key|metrics_bearer_token|contrase[nñ]as?\s+de\s+(todos|otros|usuarios)|jwt\s+secret", re.IGNORECASE),
    re.compile(r"credenciales?\s+de\s+(otros|todos|admin|operadores)", re.IGNORECASE),
)

_USER_LISTING_PATTERNS = re.compile(r"(lista|dame|muestra|exporta)\s+(los\s+)?usuarios", re.IGNORECASE)
_CONFIG_WRITE_PATTERNS = re.compile(r"(cambia|modifica|desactiva|borra)\s+(la\s+)?(configuracion|geocerca|zona|alerta)", re.IGNORECASE)

_FORBIDDEN_OUTPUT_PATTERNS = (
    re.compile(r"(activar|ejecutar|aplicar|realizar|recomiend[ao])\s+(un\s+)?(jamming|inhibici[oó]n\s+rf|spoofing|derribo|fuego\s+cin[eé]tico|secuestro\s+de\s+se[nñ]al)", re.IGNORECASE),
    re.compile(r"derribar\s+(el\s+)?dron|disparar\s+contra|hackear\s+(el\s+)?dron", re.IGNORECASE),
    re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{20,}|SECRET_KEY\s*=", re.IGNORECASE),
)

_OFF_POLICY_PATTERNS = re.compile(
    r"\b(ransomware|phishing|fabricar\s+explosivos|atacar\s+servidor)\b",
    re.IGNORECASE,
)


class AgentStructuredOutput(BaseModel):
    """Contrato estricto de salida verificado por el Guardrail de Salida."""

    summary: str = Field(min_length=5, max_length=2500)
    recommended_action: str = Field(min_length=3, max_length=120)
    priority: Literal["NORMAL", "MEDIUM", "HIGH", "CRITICAL", "INDETERMINATE", "BLOCKED"]
    confidence_note: str = Field(min_length=5, max_length=400)
    citations: list[str] = Field(default_factory=list, max_length=8)
    tools_used: list[str] = Field(default_factory=list, max_length=10)
    human_review_required: bool = True
    grounding_verified: bool = True


class InputGuardrailResult(BaseModel):
    passed: bool
    reason: str = ""
    category: str = "ok"
    sanitized_query: str = ""


class OutputGuardrailResult(BaseModel):
    passed: bool
    reason: str = ""
    output: AgentStructuredOutput


def _ascii_lower(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def evaluate_input_guardrail(
    query: str,
    user_role: Any,
    dispatch_requested: bool = False,
) -> InputGuardrailResult:
    """Evalúa prompt injection, política de seguridad y permisos RBAC antes del grafo."""
    clean_q = (query or "").strip()
    if len(clean_q) < 3 or len(clean_q) > 4000:
        return InputGuardrailResult(
            passed=False,
            reason="La consulta debe tener entre 3 y 4000 caracteres.",
            category="invalid_length",
            sanitized_query=clean_q[:200],
        )

    normalized = _ascii_lower(clean_q)

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(clean_q) or pattern.search(normalized):
            return InputGuardrailResult(
                passed=False,
                reason="Consulta bloqueada por política de seguridad (patrón de prompt injection detectado).",
                category="prompt_injection",
                sanitized_query=clean_q[:120],
            )

    if _OFF_POLICY_PATTERNS.search(normalized):
        return InputGuardrailResult(
            passed=False,
            reason="Consulta fuera del dominio defensivo C-UAS de AeroGuard.",
            category="off_policy",
            sanitized_query=clean_q[:120],
        )

    for sec_pat in _SECRET_SENSITIVE_PATTERNS:
        if sec_pat.search(clean_q) or sec_pat.search(normalized):
            return InputGuardrailResult(
                passed=False,
                reason="Política RBAC/Privacidad: prohibido consultar credenciales, hashes o secretos.",
                category="rbac_secret_denied",
                sanitized_query=clean_q[:120],
            )

    role_val = user_role.value if hasattr(user_role, "value") else str(user_role)
    if _USER_LISTING_PATTERNS.search(normalized) and not has_permission(role_val, "users:read"):
        return InputGuardrailResult(
            passed=False,
            reason=f"Permiso RBAC insuficiente: el rol '{role_val}' no posee 'users:read'.",
            category="rbac_denied",
            sanitized_query=clean_q[:120],
        )

    if _CONFIG_WRITE_PATTERNS.search(normalized) and not has_permission(role_val, "config:write"):
        return InputGuardrailResult(
            passed=False,
            reason=f"Permiso RBAC insuficiente: el rol '{role_val}' no posee 'config:write'.",
            category="rbac_denied",
            sanitized_query=clean_q[:120],
        )

    if dispatch_requested and not has_permission(role_val, "alerts:write"):
        return InputGuardrailResult(
            passed=False,
            reason=f"Permiso RBAC insuficiente: despachar eventos SOAR requiere 'alerts:write' (rol '{role_val}').",
            category="rbac_dispatch_denied",
            sanitized_query=clean_q[:120],
        )

    return InputGuardrailResult(
        passed=True,
        reason="ok",
        category="ok",
        sanitized_query=clean_q,
    )


def evaluate_output_guardrail(
    candidate: Mapping[str, Any],
    rag_citations: Sequence[Mapping[str, Any]],
    tools_used: Sequence[str],
) -> OutputGuardrailResult:
    """Valida contrato JSON Pydantic, lenguaje defensivo seguro y grounding de fuentes."""
    merged = dict(candidate)
    merged["human_review_required"] = True

    allowed_sources = {str(c.get("doc_id")) for c in rag_citations if c.get("doc_id")} | {
        str(c.get("source")) for c in rag_citations if c.get("source")
    }
    raw_cites = [str(c) for c in (merged.get("citations") or []) if str(c).strip()]
    verified_cites = [c for c in raw_cites if c in allowed_sources] if allowed_sources else []
    merged["citations"] = verified_cites[:6]
    merged["tools_used"] = [str(t) for t in (merged.get("tools_used") or tools_used)][:8]
    merged["grounding_verified"] = bool(verified_cites or merged["tools_used"])

    combined_text = f"{merged.get('summary', '')}\n{merged.get('recommended_action', '')}"
    for pattern in _FORBIDDEN_OUTPUT_PATTERNS:
        if pattern.search(combined_text):
            blocked_output = AgentStructuredOutput(
                summary=(
                    "Salida interceptada por el Guardrail de Salida: el contenido sugería acciones cinéticas/"
                    "interferencia no autorizadas o exposición de información sensible. AeroGuard solo admite "
                    "verificación visual, monitoreo, registro de evidencia y aviso al responsable de seguridad."
                ),
                recommended_action="VERIFICACION_HUMANA_Y_AVISO_SEGURIDAD",
                priority="BLOCKED",
                confidence_note="Intervención automática de seguridad (política defensiva C-UAS).",
                citations=verified_cites[:4],
                tools_used=merged["tools_used"],
                human_review_required=True,
                grounding_verified=True,
            )
            return OutputGuardrailResult(
                passed=False,
                reason="Contenido prohibido por política defensiva o seguridad interceptado en salida.",
                output=blocked_output,
            )

    try:
        validated = AgentStructuredOutput.model_validate(merged)
        return OutputGuardrailResult(passed=True, reason="ok", output=validated)
    except ValidationError as exc:
        fallback = AgentStructuredOutput(
            summary=str(merged.get("summary") or "Evaluación agéntica completada bajo modo seguro.")[:1000],
            recommended_action="VERIFICAR_DETECCION",
            priority="INDETERMINATE",
            confidence_note="Salida normalizada tras ajuste de esquema JSON estricto.",
            citations=verified_cites[:4],
            tools_used=merged["tools_used"],
            human_review_required=True,
            grounding_verified=bool(verified_cites or merged["tools_used"]),
        )
        return OutputGuardrailResult(
            passed=False,
            reason=f"Esquema de salida normalizado por Guardrail Pydantic: {exc.error_count()} errores.",
            output=fallback,
        )
