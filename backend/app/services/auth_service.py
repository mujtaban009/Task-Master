from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token,
    decode_token,
)
from app.models import User, UserRole, RefreshToken
from app.schemas import UserCreate, TokenResponse, TokenRefreshResponse

MAX_FAILED_LOGINS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

class AuthService:
    @staticmethod
    async def register(db: AsyncSession, user_in: UserCreate) -> TokenResponse:
        # Check if email is already registered (case-insensitive)
        email_clean = user_in.email.strip().lower()
        stmt = select(User).where(func.lower(User.email) == email_clean)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        # Create user (role always defaults to 'user' on public registration)
        user = User(
            full_name=user_in.full_name.strip(),
            email=email_clean,
            password_hash=get_password_hash(user_in.password),
            role=UserRole.USER,
            is_active=True,
        )
        db.add(user)
        await db.flush()  # Flush to populate user.id

        # Generate tokens
        access_token = create_access_token(subject=user.id, role=user.role.value)
        refresh_token = create_refresh_token(subject=user.id)

        # Store hashed refresh token session
        db_refresh = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(db_refresh)
        await db.commit()
        await db.refresh(user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user,
        )

    @staticmethod
    async def login(db: AsyncSession, email: str, password: str) -> TokenResponse:
        email_clean = email.strip().lower()
        stmt = select(User).where(func.lower(User.email) == email_clean)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        # Brute-force protection: refuse even the right password while locked
        if user and user.locked_until and user.locked_until > now:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Try again in 15 minutes.",
            )

        if not user or not verify_password(password, user.password_hash):
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= MAX_FAILED_LOGINS:
                    user.locked_until = now + LOCKOUT_DURATION
                    user.failed_login_attempts = 0
                await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user.failed_login_attempts = 0
        user.locked_until = None

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Please contact support.",
            )

        # Generate tokens
        access_token = create_access_token(subject=user.id, role=user.role.value)
        refresh_token = create_refresh_token(subject=user.id)

        # Store hashed refresh token session
        db_refresh = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(db_refresh)
        await db.commit()
        await db.refresh(user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user,
        )

    @staticmethod
    async def refresh_access_token(db: AsyncSession, refresh_token_str: str) -> TokenRefreshResponse:
        try:
            payload = decode_token(refresh_token_str)
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
            user_id = UUID(payload.get("sub"))
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

        # Verify hashed token exists and is valid in database
        hashed = hash_token(refresh_token_str)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == hashed,
            RefreshToken.user_id == user_id,
        )
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()

        if db_token and db_token.revoked:
            # A rotated-out token came back: it was stolen or replayed, so end every session
            await db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or expired")

        if not db_token or db_token.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or expired")

        # Fetch user
        user_stmt = select(User).where(User.id == user_id)
        user_res = await db.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found or inactive")

        # Rotate: the old refresh token is single-use, a new one replaces it
        db_token.revoked = True
        new_refresh_token = create_refresh_token(subject=user.id)
        db.add(RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ))
        await db.commit()

        new_access_token = create_access_token(subject=user.id, role=user.role.value)
        return TokenRefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    async def logout(db: AsyncSession, refresh_token_str: str, user_id: UUID) -> None:
        """Revoke refresh token session on logout."""
        hashed = hash_token(refresh_token_str)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == hashed,
            RefreshToken.user_id == user_id,
        )
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()
        if db_token:
            db_token.revoked = True
            await db.commit()
