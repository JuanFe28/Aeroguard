"""
AeroGuard — User Service
Lógica de negocio para autenticación y administración de usuarios (RF-001 a RF-004).
"""
from app.core.validation import valid_uuid

from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.models import User, UserRole
from app.core.security import hash_password, verify_password


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Busca un usuario por su nombre de usuario."""
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Busca un usuario por su correo electrónico."""
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Busca un usuario por su ID (UUID)."""
    query = select(User).where(User.id == valid_uuid(user_id))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """
    Autentica credenciales de usuario de forma segura.
    Verifica hash de contraseña mediante passlib/bcrypt.
    """
    user = await get_user_by_username(db, username)
    if not user and "@" in username:
        user = await get_user_by_email(db, username)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def update_last_login(db: AsyncSession, user_id: str) -> None:
    """Actualiza la fecha y hora del último inicio de sesión del usuario."""
    stmt = (
        update(User)
        .where(User.id == valid_uuid(user_id))
        .values(last_login=datetime.now(timezone.utc))
    )
    await db.execute(stmt)
    await db.commit()


async def update_password(db: AsyncSession, user_id: str, new_password: str, commit: bool = True) -> bool:
    """Actualiza la contraseña cifrada de un usuario."""
    hashed = hash_password(new_password)
    stmt = (
        update(User)
        .where(User.id == valid_uuid(user_id))
        .values(
            password_hash=hashed,
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db.execute(stmt)
    if commit:
        await db.commit()
    return True


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: UserRole = UserRole.OPERATOR,
) -> User:
    """Crea un nuevo usuario en la base de datos."""
    from app.core.security import validate_password_strength
    if not validate_password_strength(password):
        raise ValueError("La contraseña debe cumplir complejidad y no superar 72 bytes UTF-8.")
    hashed = hash_password(password)
    user = User(
        username=username,
        email=email,
        password_hash=hashed,
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    """Obtiene la lista paginada de usuarios."""
    query = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def set_user_active_status(db: AsyncSession, user_id: str, is_active: bool) -> Optional[User]:
    """Activa o desactiva la cuenta de un usuario."""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    user.is_active = is_active
    await db.commit()
    await db.refresh(user)
    return user
