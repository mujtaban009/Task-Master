import uuid
import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import Settings

@pytest.mark.asyncio
async def test_two_logins_in_same_second_both_succeed(client: AsyncClient):
    creds = {"username": "alice@example.com", "password": "password"}
    r1 = await client.post("/api/v1/auth/login", data=creds)
    r2 = await client.post("/api/v1/auth/login", data=creds)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["refresh_token"] != r2.json()["refresh_token"]

@pytest.mark.asyncio
async def test_password_change_requires_current_password_and_revokes_sessions(client: AsyncClient):
    email = f"pw_{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Pw User", "password": "oldpassword123"},
    )
    tokens = reg.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    missing = await client.patch("/api/v1/users/me", json={"password": "newpassword123"}, headers=headers)
    assert missing.status_code == 400
    wrong = await client.patch(
        "/api/v1/users/me",
        json={"password": "newpassword123", "current_password": "notmypassword"},
        headers=headers,
    )
    assert wrong.status_code == 400

    ok = await client.patch(
        "/api/v1/users/me",
        json={"password": "newpassword123", "current_password": "oldpassword123"},
        headers=headers,
    )
    assert ok.status_code == 200

    # The session from before the change is logged out
    refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401

    old_login = await client.post("/api/v1/auth/login", data={"username": email, "password": "oldpassword123"})
    assert old_login.status_code == 401
    new_login = await client.post("/api/v1/auth/login", data={"username": email, "password": "newpassword123"})
    assert new_login.status_code == 200

def test_jwt_secret_has_no_default(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
