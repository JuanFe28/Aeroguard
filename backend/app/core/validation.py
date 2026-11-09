"""Identificadores canónicos antes de consultar columnas UUID de PostgreSQL."""
from typing import Annotated
from uuid import UUID
from fastapi import HTTPException
from pydantic import AfterValidator


def canonical_uuid(value: str) -> str:
    return str(UUID(value))


UUIDText = Annotated[str, AfterValidator(canonical_uuid)]


def valid_uuid(value: str) -> str:
    try:
        return canonical_uuid(value)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, 'Identificador UUID inválido.')
