"""Identificadores canónicos y validación JSON estricta antes de procesar o consultar BD."""
import json
from typing import Annotated, Callable
from uuid import UUID
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import AfterValidator


def canonical_uuid(value: str) -> str:
    return str(UUID(value))


UUIDText = Annotated[str, AfterValidator(canonical_uuid)]


def valid_uuid(value: str) -> str:
    try:
        return canonical_uuid(value)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, 'Identificador UUID inválido.')


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

