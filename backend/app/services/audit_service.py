"""
AeroGuard — Audit Service (RF-029)
Mantiene un registro de auditoría inmutable mediante encadenamiento criptográfico SHA-256.
"""

import json
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.models.models import AuditLog, AuditCheckpoint
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
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    initial_head = await get_last_audit_hash(db)
    initial_count = (await db.execute(select(func.count()).select_from(AuditLog))).scalar_one()
    await db.execute(insert(AuditCheckpoint).values(id=1, head=initial_head, records=initial_count).on_conflict_do_nothing())
    # Escritura del punto de control toma un lock transaccional también en SQLite.
    from sqlalchemy import update
    await db.execute(update(AuditCheckpoint).where(AuditCheckpoint.id == 1).values(records=AuditCheckpoint.records))
    checkpoint = (await db.execute(select(AuditCheckpoint).where(AuditCheckpoint.id == 1).with_for_update().execution_options(populate_existing=True))).scalar_one()
    current_count = (await db.execute(select(func.count()).select_from(AuditLog))).scalar_one()
    current_head = await get_last_audit_hash(db)
    if checkpoint.records != current_count or checkpoint.head != current_head:
        raise ValueError("La auditoría no coincide con su punto de control persistido.")
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
    checkpoint.head = data_hash
    checkpoint.records += 1
    await db.commit()
    await db.refresh(log_entry)
    return log_entry


async def verify_audit_chain(db: AsyncSession, limit: int = 100) -> Dict[str, Any]:
    """
    Valida la cadena criptográfica de auditoría desde el registro más antiguo hasta el más reciente.
    """
    checkpoint = await db.get(AuditCheckpoint, 1)
    total = (await db.execute(select(func.count()).select_from(AuditLog))).scalar_one()
    if checkpoint and (checkpoint.records != total or checkpoint.head != await get_last_audit_hash(db)):
        return {"valid": False, "records_checked": 0, "reason": "checkpoint_mismatch", "total_records": total}
    query = select(AuditLog).order_by(AuditLog.timestamp.asc(), AuditLog.id.asc()).limit(limit)
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

    complete = len(logs) == total
    return {"valid": True if complete else None, "records_checked": len(logs), "total_records": total,
            "complete": complete, "status": "intact" if complete else "partial", "anchored": checkpoint is not None}
