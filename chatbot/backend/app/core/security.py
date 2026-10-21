from typing import Optional
from uuid import UUID
from fastapi import Header, HTTPException, status, Depends
import jwt
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.models import User

async def verify_chatbot_api_key(
    x_chatbot_api_key: Optional[str] = Header(None, alias="X-Chatbot-API-Key")
) -> str:
    """
    Enforces valid API Key authentication for the Chatbot microservice.
    All incoming requests must provide the authorized X-Chatbot-API-Key.
    """
    if not x_chatbot_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chatbot API key is missing. Provide header: 'X-Chatbot-API-Key'.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if x_chatbot_api_key.strip() != settings.CHATBOT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Chatbot API key. Access denied.",
        )
    return x_chatbot_api_key

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_chatbot_api_key),
) -> User:
    """
    Resolves the authenticated user context from a JWT Bearer access token.
    Enforces role isolation and user boundary checks.
    """
    target_user_id: Optional[str] = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials.",
            )
        # Refresh tokens are long-lived and must never authorize requests
        if payload.get("type") == "access":
            target_user_id = payload.get("sub")

    if not target_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User identity is required. Provide 'Authorization: Bearer <access token>'.",
        )

    try:
        u_uuid = UUID(target_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format.",
        )

    result = await db.execute(select(User).where(User.id == u_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user record not found.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )

    return user

