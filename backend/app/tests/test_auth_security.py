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

async def _register(client: AsyncClient, password: str = "rightpassword123") -> tuple:
    email = f"sec_{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Sec User", "password": password},
    )
    return email, reg.json()

@pytest.mark.asyncio
async def test_account_locks_after_five_failed_logins(client: AsyncClient):
    email, _ = await _register(client)
    for _ in range(5):
        bad = await client.post("/api/v1/auth/login", data={"username": email, "password": "wrongpassword"})
        assert bad.status_code == 401
    # Locked now: even the right password is refused
    locked = await client.post("/api/v1/auth/login", data={"username": email, "password": "rightpassword123"})
    assert locked.status_code == 429

@pytest.mark.asyncio
async def test_refresh_token_rotates_and_reuse_ends_all_sessions(client: AsyncClient):
    _, tokens = await _register(client)
    first = tokens["refresh_token"]

    r1 = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert r1.status_code == 200
    second = r1.json()["refresh_token"]
    assert second != first

    # Replaying the old token is treated as theft...
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401
    # ...and also kills the token the legitimate client holds
    after = await client.post("/api/v1/auth/refresh", json={"refresh_token": second})
    assert after.status_code == 401

@pytest.mark.asyncio
async def test_health_hides_database_error_details(client: AsyncClient):
    res = await client.get("/health")
    assert res.json()["database"] in ("healthy", "unhealthy")

def test_jwt_secret_has_no_default(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
