"""
AeroGuard — Users Endpoint (RF-004)
Gestión y administración de usuarios y roles (RBAC).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select, func
from app.models.models import User
from app.services.session_service import revoke_sessions
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.models import UserRole
from app.services import user_service

router = APIRouter()


class UserCreateSchema(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str
    first_name: str = Field(min_length=1, max_length=64)
    last_name: str = Field(min_length=1, max_length=64)
    role: UserRole = UserRole.OPERATOR

    @field_validator("password")
    @classmethod
    def strong_password(cls, value):
        from app.core.security import validate_password_strength
        if not validate_password_strength(value):
            raise ValueError("Contraseña débil o superior a 72 bytes UTF-8.")
        return value


class UserResponseSchema(BaseModel):
    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


@router.get("", response_model=List[UserResponseSchema], summary="Listar usuarios (RBAC: users:read)")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("users:read")),
):
    """Retorna la lista de usuarios del sistema."""
    users = await user_service.get_users(db, skip=skip, limit=limit)
    return users


@router.post("", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED, summary="Crear usuario (RBAC: users:write)")
async def create_user(
    body: UserCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("users:write")),
):
    """Crea un nuevo usuario en el sistema."""
    existing = await user_service.get_user_by_username(db, body.username)
    if existing:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado.")
    existing_email = await user_service.get_user_by_email(db, body.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")

    user = await user_service.create_user(
        db=db,
        username=body.username,
        email=body.email,
        password=body.password,
        first_name=body.first_name,
        last_name=body.last_name,
        role=body.role,
    )
    return user


@router.get("/{user_id}", response_model=UserResponseSchema, summary="Obtener detalle de usuario")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("users:read")),
):
    """Obtiene un usuario por su ID."""
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user


@router.patch("/{user_id}/status", response_model=UserResponseSchema, summary="Activar/Desactivar usuario")
async def update_status(
    user_id: str,
    active: bool,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_permission("users:write")),
):
    """Activa o desactiva la cuenta de un usuario."""
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    await protect_admin(db, user, current_user, active=active)
    user.is_active = active
    await revoke_sessions(db, user.id)
    await db.commit()
    return user


async def protect_admin(db, user, actor, active=True, role=None):
    if str(user.id) == str(actor.id) and (not active or (role is not None and role != user.role)):
        raise HTTPException(400, 'No puedes desactivar ni cambiar el rol de tu propia sesión.')
    if user.role == UserRole.ADMIN and (not active or (role is not None and role != UserRole.ADMIN)):
        count = (await db.execute(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN, User.is_active.is_(True)))).scalar_one()
        if count <= 1:
            raise HTTPException(400, 'Debe existir al menos un administrador activo.')


class UserUpdateSchema(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=64)
    last_name: str | None = Field(default=None, min_length=1, max_length=64)
    role: UserRole | None = None


@router.put('/{user_id}', response_model=UserResponseSchema)
async def update_user(user_id: str, body: UserUpdateSchema, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission('users:write'))):
    user = await user_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(404, 'Usuario no encontrado.')
    await protect_admin(db, user, current_user, role=body.role)
    if body.email:
        existing = await user_service.get_user_by_email(db, body.email)
        if existing and existing.id != user.id:
            raise HTTPException(409, 'El correo ya está registrado.')
    role_changed = body.role is not None and body.role != user.role
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(user, key, value)
    if role_changed:
        await revoke_sessions(db, user.id)
    await db.commit()
    return user
