"""
JWT Authentication Service
-----------------------------
Handles password hashing, JWT creation/verification,
and FastAPI dependency for extracting current user from token.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.db.queries import get_user_by_id

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


# ── Password Utilities ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT Utilities ──────────────────────────────────────────────────────────────

def create_access_token(user_id: int, role: str, full_name: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "full_name": full_name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


# ── FastAPI Dependency ─────────────────────────────────────────────────────────

class CurrentUser:
    def __init__(self, user_id: int, role: str, full_name: str, username: str):
        self.user_id = user_id
        self.role = role
        self.full_name = full_name
        self.username = username

    def is_manager(self) -> bool:
        return self.role == "manager"

    def is_customer(self) -> bool:
        return self.role == "customer"


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> CurrentUser:
    """FastAPI dependency — validates JWT, returns CurrentUser. Raises 401 if invalid."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(payload.get("sub", 0))
    role = payload.get("role", "")
    full_name = payload.get("full_name", "")

    # Verify user still exists
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    return CurrentUser(
        user_id=user_id,
        role=role,
        full_name=full_name,
        username=user["username"],
    )


def require_manager(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency that requires manager role."""
    if not current_user.is_manager():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Manager role required.",
        )
    return current_user
