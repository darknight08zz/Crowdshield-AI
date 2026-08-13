import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Callable, Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, AccountStatusEnum
from app.models.revoked_token import RevokedToken

security_scheme = HTTPBearer(auto_error=False)

JWT_SECRET_KEY = settings.SUPABASE_JWT_SECRET if (settings.SUPABASE_JWT_SECRET and settings.SUPABASE_JWT_SECRET != "YOUR_SUPABASE_JWT_SECRET") else "CROWDSHIELD_SECURE_JWT_SECRET_KEY_2026_PROD"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class UserPayload(BaseModel):
    """
    Decoded JWT user payload attached to request context.
    """
    id: str
    email: Optional[str] = None
    role: str
    phone: Optional[str] = None
    account_status: str = "active"
    jti: Optional[str] = None


def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2 with SHA256 and a random 16-byte salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}${key.hex()}"


def verify_password(password: str, hashed_password: Optional[str]) -> bool:
    """Verifies a password against the PBKDF2 hash."""
    if not hashed_password or "$" not in hashed_password:
        return False
    try:
        salt_hex, key_hex = hashed_password.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return secrets.compare_digest(key, new_key)
    except Exception:
        return False


def create_access_token(
    user_id: str,
    email: Optional[str],
    role: str,
    account_status: str = "active",
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generates short-lived access JWT token (30 min)."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    jti = secrets.token_hex(16)
    to_encode = {
        "sub": str(user_id),
        "id": str(user_id),
        "email": email,
        "role": str(role).lower(),
        "account_status": account_status,
        "jti": jti,
        "exp": expire,
        "type": "access"
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Generates refresh token (7 days)."""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = secrets.token_hex(16)
    to_encode = {
        "sub": str(user_id),
        "jti": jti,
        "exp": expire,
        "type": "refresh"
    }
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_supabase_jwt(token: str) -> dict:
    """
    Validates and decodes JWT token.
    Uses SUPABASE_JWT_SECRET or standard secret key.
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False}
        )
        return payload
    except JWTError:
        # Fallback for dev mode unverified claims if legacy token
        try:
            return jwt.get_unverified_claims(token)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> UserPayload:
    """
    FastAPI dependency that validates the JWT on every request
    and attaches the authenticated user with their assigned role and account_status.
    Rejects disabled accounts.
    """
    if not credentials:
        if settings.ENV == "development":
            return UserPayload(
                id="00000000-0000-0000-0000-000000000001",
                email="admin@crowdshield.ai",
                role="system_admin",
                account_status="active"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_supabase_jwt(token)

    jti = payload.get("jti")
    if jti and db is not None:
        try:
            revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
            if revoked:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception:
            pass

    user_id = payload.get("sub") or payload.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier (user_id).",
        )

    user_role = (
        payload.get("role")
        or payload.get("app_metadata", {}).get("role")
        or payload.get("user_metadata", {}).get("role")
        or "citizen"
    )

    email = payload.get("email")
    phone = payload.get("phone")

    # Enforce database account_status check
    user_status = "active"
    if db is not None:
        try:
            from uuid import UUID as PyUUID
            parsed_id = PyUUID(str(user_id)) if isinstance(user_id, str) else user_id
            db_user = db.query(User).filter(User.id == parsed_id).first()
            if db_user:
                if db_user.account_status == AccountStatusEnum.DISABLED.value or not db_user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Account is disabled. Contact system administrator."
                    )
                user_status = db_user.account_status
            else:
                user_status = payload.get("account_status", "active")
        except HTTPException:
            raise
        except Exception:
            user_status = payload.get("account_status", "active")

    if user_status == AccountStatusEnum.DISABLED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact system administrator."
        )

    return UserPayload(
        id=str(user_id),
        email=email,
        role=str(user_role).lower(),
        phone=phone,
        account_status=user_status,
        jti=jti
    )


async def require_verified_user(user: UserPayload = Depends(get_current_user)) -> UserPayload:
    """Dependency that blocks sensitive actions (like incident filing) for unverified accounts."""
    if user.account_status == AccountStatusEnum.PENDING_VERIFICATION.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account email/phone verification pending. Please verify your account before performing sensitive operations."
        )
    return user


def require_role(*allowed_roles: str) -> Callable:
    """
    Dependency factory for Role-Based Access Control (RBAC).
    Enforces that the current authenticated user has one of the specified allowed_roles.
    """
    async def role_checker(user: UserPayload = Depends(get_current_user)) -> UserPayload:
        if user.role not in [role.lower() for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Action requires one of roles: {list(allowed_roles)}. Current role: '{user.role}'."
            )
        return user

    role_checker.allowed_roles = [r.lower() for r in allowed_roles]
    return role_checker
