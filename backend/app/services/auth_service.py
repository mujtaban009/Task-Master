import hashlib
import hmac
import secrets
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
from app.services.email_service import send_email

MAX_FAILED_LOGINS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

RESET_CODE_TTL = timedelta(minutes=10)
RESET_CODE_MAX_ATTEMPTS = 5
RESET_CODE_RESEND_AFTER = timedelta(seconds=60)


def _reset_code_hash(user_id: UUID, code: str) -> str:
    # Keyed with the server secret: a leaked database row cannot be brute-forced offline
    return hmac.new(settings.JWT_SECRET_KEY.encode(), f"{user_id}:{code}".encode(), hashlib.sha256).hexdigest()

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

    @staticmethod
    async def forgot_password(db: AsyncSession, email: str) -> None:
        """Email a 6-digit reset code. Silent for unknown emails so accounts cannot be discovered."""
        user = (await db.execute(
            select(User).where(func.lower(User.email) == email.strip().lower())
        )).scalar_one_or_none()
        if not user or not user.is_active:
            return

        now = datetime.now(timezone.utc)
        # At most one email per minute per account
        if user.reset_code_expires_at and user.reset_code_expires_at - RESET_CODE_TTL + RESET_CODE_RESEND_AFTER > now:
            return

        code = f"{secrets.randbelow(1_000_000):06d}"
        user.reset_code_hash = _reset_code_hash(user.id, code)
        user.reset_code_expires_at = now + RESET_CODE_TTL
        user.reset_code_attempts = 0
        await db.commit()

        await send_email(
            user.email,
            "Your TaskMaster password reset code",
            f"Hi {user.full_name},\n\n"
            f"Your password reset code is: {code}\n\n"
            "It expires in 10 minutes. If you did not ask to reset your password, ignore this email; "
            "your password stays the same.\n\n- TaskMaster",
        )

    @staticmethod
    async def reset_password(db: AsyncSession, email: str, code: str, new_password: str) -> None:
        invalid = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code. Request a new one.",
        )
        user = (await db.execute(
            select(User).where(func.lower(User.email) == email.strip().lower())
        )).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if (
            not user or not user.is_active or not user.reset_code_hash
            or not user.reset_code_expires_at or user.reset_code_expires_at < now
            or user.reset_code_attempts >= RESET_CODE_MAX_ATTEMPTS
        ):
            raise invalid

        if not hmac.compare_digest(user.reset_code_hash, _reset_code_hash(user.id, code)):
            user.reset_code_attempts += 1
            await db.commit()
            raise invalid

        user.password_hash = get_password_hash(new_password)
        user.reset_code_hash = None
        user.reset_code_expires_at = None
        user.reset_code_attempts = 0
        # The owner proved access to the email: lift any login lockout, end all old sessions
        user.failed_login_attempts = 0
        user.locked_until = None
        await db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
        await db.commit()
