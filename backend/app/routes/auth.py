"""
Auth Routes
--------------
POST /auth/login   → returns JWT token
GET  /auth/me      → returns current user info
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
import logging

from app.db.queries import get_user_by_username
from app.auth.auth_service import verify_password, create_access_token, get_current_user, CurrentUser

router = APIRouter()
logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str
    user_id: int


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT."""
    user = get_user_by_username(request.username.strip().lower())
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token = create_access_token(
        user_id=user["id"],
        role=user["role"],
        full_name=user["full_name"],
    )

    logger.info(f"Login successful: user={user['username']}, role={user['role']}")
    return LoginResponse(
        access_token=token,
        role=user["role"],
        full_name=user["full_name"],
        user_id=user["id"],
    )


@router.get("/me")
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Return info about the currently authenticated user."""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role,
        "full_name": current_user.full_name,
    }
