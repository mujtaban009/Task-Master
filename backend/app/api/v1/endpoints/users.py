from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import get_password_hash, verify_password
from app.db.session import get_db
from app.models import RefreshToken, User
from app.schemas import UserResponse, UserUpdate

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Retrieve profile of currently authenticated user."""
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update profile information for currently authenticated user."""
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name
    if user_in.password is not None:
        # A stolen access token alone must not be enough to take over the account
        if not user_in.current_password or not verify_password(user_in.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )
        current_user.password_hash = get_password_hash(user_in.password)
        # Log out every existing session
        await db.execute(
            update(RefreshToken).where(RefreshToken.user_id == current_user.id).values(revoked=True)
        )

    await db.commit()
    await db.refresh(current_user)
    return current_user
