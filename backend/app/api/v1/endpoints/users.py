"""
AeroGuard — Users Endpoint (RF-004)
Gestión y administración de usuarios y roles (RBAC).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.models import UserRole
from app.services import user_service

router = APIRouter()


class UserCreateSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: UserRole = UserRole.OPERATOR


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
    skip: int = 0,
    limit: int = 50,
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
    user = await user_service.set_user_active_status(db, user_id, active)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user
