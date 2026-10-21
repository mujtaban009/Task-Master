import re
import uuid
import pytest
from httpx import AsyncClient

from app.services import auth_service


@pytest.fixture
def outbox(monkeypatch):
    """Captures reset emails instead of sending them."""
    sent = []

    async def fake_send(to, subject, body):
        sent.append({"to": to, "code": re.search(r"\b(\d{6})\b", body).group(1)})
        return True

    monkeypatch.setattr(auth_service, "send_email", fake_send)
    return sent


async def _register(client: AsyncClient) -> tuple:
    email = f"reset_{uuid.uuid4().hex[:8]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Reset User", "password": "oldpassword123"},
    )
    return email, reg.json()["refresh_token"]


@pytest.mark.asyncio
async def test_reset_with_emailed_code_changes_password_and_ends_sessions(client: AsyncClient, outbox):
    email, old_refresh = await _register(client)

    res = await client.post("/api/v1/auth/forgot-password", json={"email": email.upper()})
    assert res.status_code == 200
    assert len(outbox) == 1 and outbox[0]["to"] == email

    ok = await client.post("/api/v1/auth/reset-password",
                           json={"email": email, "code": outbox[0]["code"], "new_password": "newpassword123"})
    assert ok.status_code == 200

    assert (await client.post("/api/v1/auth/login", data={"username": email, "password": "newpassword123"})).status_code == 200
    assert (await client.post("/api/v1/auth/login", data={"username": email, "password": "oldpassword123"})).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})).status_code == 401
    # The code is single-use
    again = await client.post("/api/v1/auth/reset-password",
                              json={"email": email, "code": outbox[0]["code"], "new_password": "thirdpassword1"})
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_unknown_email_gets_same_answer_and_no_email(client: AsyncClient, outbox):
    known, _ = await _register(client)
    a = await client.post("/api/v1/auth/forgot-password", json={"email": known})
    b = await client.post("/api/v1/auth/forgot-password", json={"email": "nobody-here@example.com"})
    assert a.json() == b.json()
    assert [m["to"] for m in outbox] == [known]


@pytest.mark.asyncio
async def test_code_is_dead_after_five_wrong_guesses(client: AsyncClient, outbox):
    email, _ = await _register(client)
    await client.post("/api/v1/auth/forgot-password", json={"email": email})
    real = outbox[0]["code"]
    wrong = f"{(int(real) + 1) % 1_000_000:06d}"
    for _ in range(5):
        bad = await client.post("/api/v1/auth/reset-password",
                                json={"email": email, "code": wrong, "new_password": "newpassword123"})
        assert bad.status_code == 400
    late = await client.post("/api/v1/auth/reset-password",
                             json={"email": email, "code": real, "new_password": "newpassword123"})
    assert late.status_code == 400


@pytest.mark.asyncio
async def test_second_request_within_a_minute_sends_nothing(client: AsyncClient, outbox):
    email, _ = await _register(client)
    await client.post("/api/v1/auth/forgot-password", json={"email": email})
    await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert len(outbox) == 1
