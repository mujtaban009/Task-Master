from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas import (
    UserCreate,
    TokenResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.auth_service import AuthService

router = APIRouter()

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account with validated credentials."""
    return await AuthService.register(db, user_in)

@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with username (email) and password to obtain JWT access and refresh tokens."""
    return await AuthService.login(db, form_data.username, form_data.password)

@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    refresh_in: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a newly minted access token."""
    return await AuthService.refresh_access_token(db, refresh_in.refresh_token)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    refresh_in: TokenRefreshRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current refresh token session and log out."""
    await AuthService.logout(db, refresh_in.refresh_token, current_user.id)
    return None

@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Email a 6-digit reset code. Same answer whether or not the account exists."""
    await AuthService.forgot_password(db, body.email)
    return {"detail": "If an account exists for that email, a reset code has been sent."}

@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Set a new password using the emailed code; signs out every existing session."""
    await AuthService.reset_password(db, body.email, body.code, body.new_password)
    return {"detail": "Password updated. You can now sign in with your new password."}
