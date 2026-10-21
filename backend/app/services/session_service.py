"""Estado de autenticación persistente. No almacena tokens en texto plano."""

import hashlib
import time
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.models.models import AuthAttempt, AuthState
from app.core.config import settings


async def state_for(db, user_id):
    state = await db.get(AuthState, user_id)
    if state is None:
        insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
        await db.execute(insert(AuthState).values(user_id=user_id, version=0).on_conflict_do_nothing())
        await db.flush()
        state = await db.get(AuthState, user_id)
    return state


async def revoke_sessions(db, user_id):
    state = await state_for(db, user_id)
    from sqlalchemy import update
    await db.execute(update(AuthState).where(AuthState.user_id == user_id).values(
        version=AuthState.version + 1, reset_digest=None, reset_expires_at=None))
    await db.flush()

    from app.models.models import User
    user = await db.get(User, user_id)
    if user:
        from app.api.v1.endpoints.websocket import manager
        await manager.close_user(user.username)


def digest_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def allow_auth_attempt(db, address, path):
    """Contador atómico por IP/ruta y ventana; compartido por procesos sobre la misma BD."""
    bucket = int(time.time()) // settings.AUTH_RATE_WINDOW_SECONDS
    key = hashlib.sha256(f"{address}|{path}".encode()).hexdigest()
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    statement = insert(AuthAttempt).values(key=key, bucket=bucket, count=1)
    statement = statement.on_conflict_do_update(
        index_elements=[AuthAttempt.key, AuthAttempt.bucket], set_={"count": AuthAttempt.count + 1}
    ).returning(AuthAttempt.count)
    count = (await db.execute(statement)).scalar_one()
    await db.execute(delete(AuthAttempt).where(AuthAttempt.bucket < bucket - 2))
    await db.commit()
    return count <= settings.AUTH_RATE_LIMIT
