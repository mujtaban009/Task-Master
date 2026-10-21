import asyncio
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import get_current_user

ADMIN_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"  # public in database/init/02_seed.sql

def _rejected_status(authorization):
    # db=None: every request here must be rejected before the user lookup
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(authorization=authorization, db=None, _api_key="ignored"))
    return exc.value.status_code

def _token(token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": ADMIN_ID, "type": token_type, "iat": now, "exp": now + timedelta(minutes=5)}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def test_request_without_token_is_rejected():
    assert _rejected_status(None) == 401

def test_refresh_token_cannot_authorize_requests():
    assert _rejected_status(f"Bearer {_token('refresh')}") == 401

def test_token_signed_with_other_secret_is_rejected():
    forged = jwt.encode({"sub": ADMIN_ID, "type": "access"}, "not-the-secret", algorithm="HS256")
    assert _rejected_status(f"Bearer {forged}") == 401
