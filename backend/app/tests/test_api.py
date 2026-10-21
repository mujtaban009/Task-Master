import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["database"] == "healthy"

@pytest.mark.asyncio
async def test_user_registration(client: AsyncClient):
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test Runner", "password": "securepassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == email

@pytest.mark.asyncio
async def test_duplicate_registration_rejected(client: AsyncClient):
    payload = {"email": "alice@example.com", "full_name": "Alice Duplicate", "password": "securepassword123"}
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_user_login_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "password"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alice@example.com"

    # Also verify invalid credentials return 401
    bad_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "wrongpassword"},
    )
    assert bad_res.status_code == 401

@pytest.mark.asyncio
async def test_task_crud_and_isolation(client: AsyncClient):
    import uuid
    # Register user 1
    u1_email = f"u1_{uuid.uuid4().hex[:8]}@example.com"
    r1 = await client.post(
        "/api/v1/auth/register",
        json={"email": u1_email, "full_name": "User One", "password": "securepassword123"},
    )
    assert r1.status_code == 201
    t1_token = r1.json()["access_token"]
    u1_headers = {"Authorization": f"Bearer {t1_token}"}

    # Register user 2
    u2_email = f"u2_{uuid.uuid4().hex[:8]}@example.com"
    r2 = await client.post(
        "/api/v1/auth/register",
        json={"email": u2_email, "full_name": "User Two", "password": "securepassword123"},
    )
    assert r2.status_code == 201
    t2_token = r2.json()["access_token"]
    u2_headers = {"Authorization": f"Bearer {t2_token}"}

    # User 1 creates task
    task_res = await client.post(
        "/api/v1/tasks",
        json={"title": "Private Task for User 1", "priority": "high"},
        headers=u1_headers,
    )
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]

    # User 2 attempts to retrieve User 1's task (must be 404 / access denied)
    unauth_get = await client.get(f"/api/v1/tasks/{task_id}", headers=u2_headers)
    assert unauth_get.status_code == 404

    # User 2 attempts to update User 1's task
    unauth_patch = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Hacked Title"},
        headers=u2_headers,
    )
    assert unauth_patch.status_code == 404

    # User 1 lists tasks -> returns the task
    list_res = await client.get("/api/v1/tasks", headers=u1_headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # User 1 summary
    summary_res = await client.get("/api/v1/tasks/summary", headers=u1_headers)
    assert summary_res.status_code == 200
    assert summary_res.json()["total_tasks"] >= 1

    # User 1 marks completed
    complete_res = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "completed"},
        headers=u1_headers,
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["completed_at"] is not None

    # User 1 deletes task
    del_res = await client.delete(f"/api/v1/tasks/{task_id}", headers=u1_headers)
    assert del_res.status_code == 204
