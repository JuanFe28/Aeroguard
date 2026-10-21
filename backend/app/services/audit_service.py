"""
AeroGuard — Audit Service (RF-029)
Mantiene un registro de auditoría inmutable mediante encadenamiento criptográfico SHA-256.
"""

import json
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.models import AuditLog
from app.core.security import compute_hash


async def get_last_audit_hash(db: AsyncSession) -> str:
    """Obtiene el hash del último registro de auditoría para encadenar."""
    query = select(AuditLog.data_hash).order_by(desc(AuditLog.timestamp)).limit(1)
    result = await db.execute(query)
    last_hash = result.scalar_one_or_none()
    return last_hash or ("0" * 64)


async def log_audit(
    db: AsyncSession,
    action: str,
    resource: str,
    username: str,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """
    Registra un evento de auditoría garantizando integridad criptográfica (SHA-256 chain).
    """
    details = details or {}
    prev_hash = await get_last_audit_hash(db)

    # Serialización canónica de los datos del registro
    raw_payload = f"{prev_hash}|{username}|{action}|{resource}|{resource_id or ''}|{json.dumps(details, sort_keys=True)}"
    data_hash = compute_hash(raw_payload, prev_hash)

    log_entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        data_hash=data_hash,
        prev_hash=prev_hash,
    )

    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)
    return log_entry


async def verify_audit_chain(db: AsyncSession, limit: int = 100) -> Dict[str, Any]:
    """
    Valida la cadena criptográfica de auditoría desde el registro más antiguo hasta el más reciente.
    """
    query = select(AuditLog).order_by(AuditLog.timestamp.asc()).limit(limit)
    result = await db.execute(query)
    logs: List[AuditLog] = result.scalars().all()

    if not logs:
        return {"valid": True, "records_checked": 0, "status": "empty"}

    expected_prev = "0" * 64
    for i, log in enumerate(logs):
        if i == 0 and log.prev_hash != expected_prev:
            return {"valid": False, "compromised_id": log.id, "reason": "genesis_mismatch"}
        elif i > 0 and log.prev_hash != logs[i - 1].data_hash:
            return {"valid": False, "compromised_id": log.id, "reason": "broken_chain"}

        raw_payload = f"{log.prev_hash}|{log.username}|{log.action}|{log.resource}|{log.resource_id or ''}|{json.dumps(log.details, sort_keys=True)}"
        expected_hash = compute_hash(raw_payload, log.prev_hash)
        if log.data_hash != expected_hash:
            return {"valid": False, "compromised_id": log.id, "reason": "hash_tampered"}

    return {"valid": True, "records_checked": len(logs), "status": "intact"}
