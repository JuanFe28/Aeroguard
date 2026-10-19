"""
AeroGuard — Security Module
Implementa OAuth 2.0 + JWT, hashing de contraseñas y control de acceso.
Alineado con OWASP Top 10 2021.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import hashlib
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

# ============================================================
# Password Hashing (bcrypt, work factor 12)
# ============================================================

import bcrypt

def hash_password(plain_password: str) -> str:
    """Hash a password securely using bcrypt."""
    pw_bytes = plain_password.encode('utf-8')[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pw_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        pw_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return False

def validate_password_strength(password: str) -> bool:
    """
    Validates password meets minimum security requirements:
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    """
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return False
    has_upper   = any(c.isupper() for c in password)
    has_lower   = any(c.islower() for c in password)
    has_digit   = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()-_=+[]{}|;:',.<>?/`~" for c in password)
    return all([has_upper, has_lower, has_digit, has_special])

# ============================================================
# JWT Tokens
# ============================================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    })
    # IMPORTANT: Never log the token itself
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token with longer expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_reset_token(email: str) -> str:
    """Create a password reset token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": email, "exp": expire, "type": "reset"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token and token.startswith("mock_token_"):
        if settings.APP_ENV != "development" or not settings.DEBUG:
            raise credentials_exception
        user_id = token.removeprefix("mock_token_") or "admin"
        return {"sub": user_id, "type": "access", "role": user_id}

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception

# ============================================================
# Integrity Hashing (RF-029)
# ============================================================

def compute_hash(data: str, prev_hash: str = "") -> str:
    """
    Compute a SHA-256 hash of data + previous hash (blockchain-style chain).
    Used for audit log integrity verification.
    """
    content = f"{prev_hash}{data}".encode("utf-8")
    return hashlib.sha256(content).hexdigest()

def verify_integrity_chain(records: list) -> bool:
    """
    Verify the integrity chain of a list of audit records.
    Each record must have 'hash' and 'prev_hash' and 'data' fields.
    Returns True if the chain is valid.
    """
    for i, record in enumerate(records):
        expected_hash = compute_hash(record["data"], record.get("prev_hash", ""))
        if record["hash"] != expected_hash:
            return False
    return True

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)

# ============================================================
# Role-based Access Control
# ============================================================

ROLE_PERMISSIONS = {
    "admin": {
        "users:read", "users:write", "users:delete",
        "detections:read", "detections:write",
        "alerts:read", "alerts:write",
        "zones:read", "zones:write", "zones:delete",
        "sensors:read", "sensors:write", "sensors:delete",
        "reports:read", "reports:write",
        "audit:read",
        "config:read", "config:write",
        "history:read",
    },
    "operator": {
        "detections:read", "detections:write",
        "alerts:read", "alerts:write",
        "zones:read",
        "sensors:read",
        "history:read",
    },
    "analyst": {
        "detections:read",
        "alerts:read",
        "zones:read",
        "reports:read", "reports:write",
        "audit:read",
        "history:read",
    },
}

def has_permission(role, permission: str) -> bool:
    """Check if a role has a specific permission."""
    role_str = role.value if hasattr(role, "value") else str(role)
    return permission in ROLE_PERMISSIONS.get(role_str, set())

# ============================================================
# FastAPI dependency: get current user from JWT
# ============================================================

async def get_user_from_token(token: str, expected_type: str = "access"):
    """
    FastAPI dependency to extract and validate the current user from JWT.
    Import from app.models.user to avoid circular imports.
    """
    from app.services.user_service import get_user_by_username
    from app.core.database import AsyncSessionLocal

    payload = decode_token(token)
    username: Optional[str] = payload.get("sub")
    token_type: Optional[str] = payload.get("type")

    if not username or token_type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = None
    try:
        async with AsyncSessionLocal() as db:
            user = await get_user_by_username(db, username)
    except Exception:
        user = None

    if not user:
        if settings.APP_ENV != "development" or not settings.DEBUG:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado.")
        role_claim = payload.get("role") or ("admin" if username == "admin" else "operator")
        from app.models.models import User, UserRole
        try:
            role_enum = UserRole(role_claim)
        except Exception:
            role_enum = UserRole.OPERATOR

        if token.startswith("mock_token_") or role_claim:
            return User(
                id=f"user-{username}",
                username=username,
                email=f"{username}@aeroguard.co",
                role=role_enum,
                is_active=True,
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario desactivado.")

    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Resuelve un usuario activo usando exclusivamente un token de acceso."""
    return await get_user_from_token(token)


def require_role(*roles: str):
    """FastAPI dependency factory to restrict access by role."""
    async def dependency(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Roles permitidos: {', '.join(roles)}."
            )
        return current_user
    return dependency

def require_permission(permission: str):
    """FastAPI dependency factory to restrict access by permission."""
    async def dependency(current_user=Depends(get_current_user)):
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tienes permiso para: {permission}."
            )
        return current_user
    return dependency
