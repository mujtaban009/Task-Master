import uuid
import pytest
from httpx import AsyncClient
from app.core.security import create_access_token

ADMIN_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

async def _chat(client: AsyncClient, headers: dict, content: str) -> dict:
    res = await client.post("/api/v1/chat/message", json={"content": content}, headers=headers)
    assert res.status_code == 200
    return res.json()

async def _task_titles(client: AsyncClient, headers: dict) -> list:
    res = await client.get("/api/v1/tasks", params={"page_size": 100}, headers=headers)
    return [t["title"] for t in res.json()["items"]]

@pytest.mark.asyncio
async def test_admin_agent_adds_own_task_and_assigns_to_user(client: AsyncClient):
    admin_headers = {"Authorization": f"Bearer {create_access_token(subject=ADMIN_ID, role='admin')}"}
    tag = uuid.uuid4().hex[:6]
    worker_email = f"worker_{tag}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": worker_email, "full_name": "Flow Worker", "password": "password123"},
    )
    worker_headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Admin adds a task to their own panel; the title keeps its capital letters
    own = await _chat(client, admin_headers, f"Add task Review Release Notes {tag} to my tasks")
    assert "admin_create_task" in own["tools_executed"]
    assert f"Review Release Notes {tag}" in await _task_titles(client, admin_headers)

    # Admin creates a task and assigns it to the user
    assigned = await _chat(client, admin_headers, f"Create task Fix Login Bug {tag} and assign it to {worker_email}")
    assert "admin_create_task" in assigned["tools_executed"]
    worker_titles = await _task_titles(client, worker_headers)
    assert f"Fix Login Bug {tag}" in worker_titles
    assert f"Review Release Notes {tag}" not in worker_titles

    # The user's agent sees only the user's own tasks
    reply = (await _chat(client, worker_headers, "Show my tasks"))["assistant_message"]["content"]
    assert f"Fix Login Bug {tag}" in reply
    assert f"Review Release Notes {tag}" not in reply
