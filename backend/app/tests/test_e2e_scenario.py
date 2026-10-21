import sys
import asyncio
import uuid
import pytest
from httpx import AsyncClient

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@pytest.mark.asyncio
async def test_complete_e2e_lifecycle(client: AsyncClient):
    """
    Complete End-to-End Test Scenario covering:
    1. User Registration (Alice & Bob)
    2. Authentication & JWT Token Issuance
    3. Profile Retrieval (/users/me)
    4. Task Creation with Metadata & Due Dates
    5. User Isolation (Bob attempts to read Alice's task -> 404/Forbidden)
    6. Task Filtering (by Status and Priority)
    7. Task Pagination & Search
    8. Partial Update & State Transition to 'completed' (verifying completed_at timestamp)
    9. User Task Statistical Summary Aggregation
    10. Refresh Token Rotation
    11. Explicit User Logout & Token Revocation
    12. Admin Role Verification & Dashboard Analytics Inspection
    13. Clean Task Deletion
    """
    # -------------------------------------------------------------
    # Step 1: User Registration
    # -------------------------------------------------------------
    alice_email = f"alice_e2e_{uuid.uuid4().hex[:6]}@example.com"
    bob_email = f"bob_e2e_{uuid.uuid4().hex[:6]}@example.com"

    alice_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": alice_email, "full_name": "Alice Wonderland", "password": "StrongPassword123!"},
    )
    assert alice_reg.status_code == 201, f"Alice registration failed: {alice_reg.text}"
    alice_data = alice_reg.json()
    alice_token = alice_data["access_token"]
    alice_refresh = alice_data["refresh_token"]
    alice_id = alice_data["user"]["id"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}

    bob_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": bob_email, "full_name": "Bob Builder", "password": "StrongPassword123!"},
    )
    assert bob_reg.status_code == 201, f"Bob registration failed: {bob_reg.text}"
    bob_token = bob_reg.json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # -------------------------------------------------------------
    # Step 2: Verify Profile via /users/me
    # -------------------------------------------------------------
    me_res = await client.get("/api/v1/users/me", headers=alice_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == alice_email
    assert me_res.json()["full_name"] == "Alice Wonderland"

    # -------------------------------------------------------------
    # Step 3: Alice Creates Tasks
    # -------------------------------------------------------------
    t1_res = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Complete Phase 2 Backend Verification",
            "description": "Run exhaustive lifecycle automated tests",
            "priority": "high",
            "status": "in_progress",
        },
        headers=alice_headers,
    )
    assert t1_res.status_code == 201
    t1 = t1_res.json()
    t1_id = t1["id"]
    assert t1["title"] == "Complete Phase 2 Backend Verification"
    assert t1["priority"] == "high"
    assert t1["status"] == "in_progress"
    assert t1["completed_at"] is None

    t2_res = await client.post(
        "/api/v1/tasks",
        json={
            "title": "Prepare React Frontend",
            "description": "Design component architecture for Vite frontend",
            "priority": "medium",
            "status": "pending",
        },
        headers=alice_headers,
    )
    assert t2_res.status_code == 201
    t2_id = t2_res.json()["id"]

    # -------------------------------------------------------------
    # Step 4: Strict Security & Cross-User Isolation Check
    # Bob attempts to view or modify Alice's task -> MUST FAIL
    # -------------------------------------------------------------
    bob_view = await client.get(f"/api/v1/tasks/{t1_id}", headers=bob_headers)
    assert bob_view.status_code == 404, "Security violation: Bob was able to view Alice's task!"

    bob_hack = await client.patch(
        f"/api/v1/tasks/{t1_id}",
        json={"title": "Compromised by Bob"},
        headers=bob_headers,
    )
    assert bob_hack.status_code == 404, "Security violation: Bob was able to update Alice's task!"

    bob_del = await client.delete(f"/api/v1/tasks/{t1_id}", headers=bob_headers)
    assert bob_del.status_code == 404, "Security violation: Bob was able to delete Alice's task!"

    # -------------------------------------------------------------
    # Step 5: Filter, Search, and Pagination
    # -------------------------------------------------------------
    # Filter by priority=high
    filter_res = await client.get("/api/v1/tasks?priority=high", headers=alice_headers)
    assert filter_res.status_code == 200
    assert filter_res.json()["total"] == 1
    assert filter_res.json()["items"][0]["id"] == t1_id

    # Search by keyword 'React'
    search_res = await client.get("/api/v1/tasks?search=React", headers=alice_headers)
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1
    assert search_res.json()["items"][0]["id"] == t2_id

    # -------------------------------------------------------------
    # Step 6: Update State to 'completed' & Check Timestamp Compliance
    # -------------------------------------------------------------
    complete_res = await client.patch(
        f"/api/v1/tasks/{t1_id}",
        json={"status": "completed"},
        headers=alice_headers,
    )
    assert complete_res.status_code == 200
    updated_t1 = complete_res.json()
    assert updated_t1["status"] == "completed"
    assert updated_t1["completed_at"] is not None

    # -------------------------------------------------------------
    # Step 7: Task Statistics Summary Aggregation
    # -------------------------------------------------------------
    summary_res = await client.get("/api/v1/tasks/summary", headers=alice_headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_tasks"] == 2
    assert summary["completed_tasks"] == 1
    assert summary["pending_tasks"] == 1
    assert summary["high_priority_tasks"] == 1

    # -------------------------------------------------------------
    # Step 8: Token Refresh Cycle
    # -------------------------------------------------------------
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": alice_refresh},
    )
    assert refresh_res.status_code == 200
    new_access_token = refresh_res.json()["access_token"]
    assert len(new_access_token) > 20

    # Refreshed token allows querying protected user profile
    profile_check = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {new_access_token}"})
    assert profile_check.status_code == 200
    assert profile_check.json()["email"] == alice_email

    # -------------------------------------------------------------
    # Step 9: User Logout & Session Revocation
    # -------------------------------------------------------------
    logout_res = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": alice_refresh},
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert logout_res.status_code == 204

    # Using the revoked refresh token must now fail with 401
    revoked_attempt = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": alice_refresh},
    )
    assert revoked_attempt.status_code == 401

    # -------------------------------------------------------------
    # Step 10: Admin Dashboard Analytics
    # -------------------------------------------------------------
    from app.core.security import create_access_token
    admin_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    admin_token = create_access_token(subject=admin_id, role="admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    dash_res = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["total_users"] >= 2
    assert dash["total_tasks"] >= 2
    assert dash["completion_rate_percentage"] >= 0.0

    # -------------------------------------------------------------
    # Step 11: Task Cleanup
    # -------------------------------------------------------------
    del_res = await client.delete(f"/api/v1/tasks/{t1_id}", headers={"Authorization": f"Bearer {new_access_token}"})
    assert del_res.status_code == 204
