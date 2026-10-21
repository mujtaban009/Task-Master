import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_admin_endpoints(client: AsyncClient):
    import uuid
    # Create regular user
    reg_user_email = f"norm_{uuid.uuid4().hex[:8]}@example.com"
    r1 = await client.post(
        "/api/v1/auth/register",
        json={"email": reg_user_email, "full_name": "Normal User", "password": "securepassword123"},
    )
    assert r1.status_code == 201
    norm_token = r1.json()["access_token"]
    norm_headers = {"Authorization": f"Bearer {norm_token}"}

    # Normal user attempts to access /admin/dashboard -> must be 403 Forbidden
    forbidden_res = await client.get("/api/v1/admin/dashboard", headers=norm_headers)
    assert forbidden_res.status_code == 403

    # Generate admin JWT directly using admin subject UUID from seed
    from app.core.security import create_access_token
    admin_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    admin_token = create_access_token(subject=admin_id, role="admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin accesses dashboard
    dash_res = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "total_users" in dash_data
    assert "total_tasks" in dash_data
    assert "completion_rate_percentage" in dash_data
    assert dash_data["total_users"] >= 2

    # Admin lists users
    users_res = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert users_res.status_code == 200
    assert len(users_res.json()) >= 2

    # Admin retrieves individual user by ID
    norm_user_id = r1.json()["user"]["id"]
    single_user_res = await client.get(f"/api/v1/admin/users/{norm_user_id}", headers=admin_headers)
    assert single_user_res.status_code == 200
    assert single_user_res.json()["email"] == reg_user_email

    # Admin deactivates and reactivates user
    deact_res = await client.patch(
        f"/api/v1/admin/users/{norm_user_id}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["is_active"] is False

    react_res = await client.patch(
        f"/api/v1/admin/users/{norm_user_id}/status",
        json={"is_active": True},
        headers=admin_headers,
    )
    assert react_res.status_code == 200
    assert react_res.json()["is_active"] is True
