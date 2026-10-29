"""
AeroGuard — Audit Endpoint (RF-029)
Consulta y verificación criptográfica de la pista de auditoría inmutable.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.models import AuditLog
from app.services.audit_service import verify_audit_chain

router = APIRouter()


@router.get("", summary="Listar registros de auditoría (RF-029)")
async def list_audit_logs(
    username: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("audit:read")),
):
    """Lista eventos del sistema con sus hashes SHA-256 de integridad."""
    query = select(AuditLog).order_by(desc(AuditLog.timestamp)).offset(skip).limit(limit)
    if username:
        query = query.where(AuditLog.username == username)
    if action:
        query = query.where(AuditLog.action == action)
    if resource:
        query = query.where(AuditLog.resource == resource)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/verify", summary="Verificar integridad criptográfica de la cadena SHA-256 (RF-029)")
async def verify_chain(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("audit:read")),
):
    """
    Verifica matemáticamente que la cadena de registros no haya sido alterada ni truncada.
    """
    verification_result = await verify_audit_chain(db, limit=limit)
    return verification_result
