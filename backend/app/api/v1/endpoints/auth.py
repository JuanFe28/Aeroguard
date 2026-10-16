"""
AeroGuard — Auth API Endpoint (RF-001, RF-002, RF-003)
Implementa OAuth 2.0 Password Flow + JWT + gestión de contraseñas.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    verify_password, create_access_token, create_refresh_token,
    create_reset_token, decode_token, get_current_user,
    hash_password, validate_password_strength
)
from app.core.config import settings

router = APIRouter()


# ============================================================
# Schemas
# ============================================================

class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    expires_in:    int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    user:          dict

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_strength(cls, v):
        if not validate_password_strength(v):
            raise ValueError("La contraseña debe tener al menos 8 caracteres, mayúsculas, minúsculas, números y un carácter especial.")
        return v

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_strength(cls, v):
        if not validate_password_strength(v):
            raise ValueError("La contraseña no cumple los requisitos de seguridad.")
        return v

class RefreshRequest(BaseModel):
    refresh_token: str


# ============================================================
# Endpoints
# ============================================================

@router.post(
    "/token",
    response_model=TokenResponse,
    summary="RF-001: Iniciar Sesión",
    description="OAuth 2.0 Password Flow. Devuelve access_token y refresh_token JWT."
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Autentica al usuario y devuelve tokens JWT.
    - Verifica credenciales contra la base de datos
    - Registra el intento en auditoría
    - Actualiza last_login
    - No revela si el usuario existe o no (seguridad OWASP A07)
    """
    from app.services.user_service import authenticate_user, update_last_login
    from app.services.audit_service import log_audit
    from app.core.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            user = await authenticate_user(db, form_data.username, form_data.password)

            if not user:
                # Audit failed login attempt
                try:
                    await log_audit(
                        db=db,
                        user_id=None,
                        username=form_data.username,
                        action="LOGIN_FAILED",
                        resource="auth",
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent"),
                        details={"reason": "invalid_credentials"},
                    )
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales incorrectas.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuario desactivado. Contacta al administrador."
                )

            # Create tokens
            token_data = {"sub": user.username, "role": user.role}
            access_token  = create_access_token(token_data)
            refresh_token = create_refresh_token(token_data)

            # Update last login
            await update_last_login(db, user.id)

            # Audit successful login
            await log_audit(
                db=db,
                user_id=user.id,
                username=user.username,
                action="LOGIN",
                resource="auth",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                user={
                    "id":         str(user.id),
                    "username":   str(user.username),
                    "email":      str(user.email),
                    "first_name": str(user.first_name),
                    "last_name":  str(user.last_name),
                    "role":       user.role,
                }
            )
    except HTTPException:
        raise
    except (ConnectionRefusedError, OSError) as conn_err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", summary="Renovar Access Token")
async def refresh_token(body: RefreshRequest):
    """Renueva el access token usando el refresh token."""
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Token de tipo incorrecto.")
    new_token = create_access_token({"sub": payload["sub"], "role": payload.get("role")})
    return {"access_token": new_token, "token_type": "bearer"}


@router.post("/logout", summary="Cerrar Sesión", status_code=204)
async def logout(request: Request, current_user=Depends(get_current_user)):
    """
    Registra el cierre de sesión en auditoría.
    (En producción: añadir token a blacklist Redis)
    """
    from app.services.audit_service import log_audit
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await log_audit(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            action="LOGOUT",
            resource="auth",
            ip_address=request.client.host if request.client else None,
        )


@router.get("/me", summary="Perfil del usuario actual")
async def get_me(current_user=Depends(get_current_user)):
    """Devuelve la información del usuario autenticado."""
    return {
        "id":         current_user.id,
        "username":   current_user.username,
        "email":      current_user.email,
        "first_name": current_user.first_name,
        "last_name":  current_user.last_name,
        "role":       current_user.role,
        "is_active":  current_user.is_active,
        "last_login": current_user.last_login,
    }


@router.post("/change-password", summary="RF-002: Cambiar Contraseña", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user=Depends(get_current_user),
):
    """Cambia la contraseña del usuario autenticado."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta.")

    from app.services.user_service import update_password
    from app.services.audit_service import log_audit
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await update_password(db, current_user.id, body.new_password)
        await log_audit(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            action="CHANGE_PASSWORD",
            resource="auth",
            ip_address=request.client.host if request.client else None,
        )


@router.post("/request-reset", summary="RF-003: Solicitar Recuperación de Contraseña", status_code=202)
async def request_password_reset(body: PasswordResetRequest):
    """
    Envía un correo de recuperación de contraseña.
    Siempre retorna 202 para no revelar si el correo existe (OWASP A07).
    """
    from app.services.user_service import get_user_by_email
    from app.services.email_service import send_reset_email
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        user = await get_user_by_email(db, body.email)
        if user and user.is_active:
            user_email = str(user.email)
            token = create_reset_token(user_email)
            await send_reset_email(user_email, token)

    return {"message": "Si el correo existe en el sistema, recibirás las instrucciones."}


@router.post("/reset-password", summary="RF-003: Resetear Contraseña", status_code=204)
async def reset_password(body: PasswordResetConfirm):
    """Aplica la nueva contraseña usando el token de recuperación."""
    payload = decode_token(body.token)
    if payload.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Token de tipo incorrecto.")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="Token no contiene correo válido.")

    from app.services.user_service import get_user_by_email, update_password
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        user = await get_user_by_email(db, str(email))
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        await update_password(db, str(user.id), body.new_password)
