import pytest

pytestmark = pytest.mark.asyncio


async def _login(client, email, password):
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp


async def test_login_fails_for_unknown_user(client):
    resp = await _login(client, "nobody@x.com", "whatever123")
    assert resp.status_code == 401


async def test_admin_can_register_new_user_and_new_user_can_login(client, seed_admin):
    admin_login = await _login(client, seed_admin["email"], seed_admin["password"])
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "analyst@sentinelguard.ai",
            "password": "AnalystPass1!",
            "full_name": "Jane Analyst",
            "role": "ANALYST",
            "department": "Finance",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "analyst@sentinelguard.ai"
    assert body["role"] == "ANALYST"

    login = await _login(client, "analyst@sentinelguard.ai", "AnalystPass1!")
    assert login.status_code == 200
    tokens = login.json()
    assert "access_token" in tokens and "refresh_token" in tokens


async def test_non_admin_cannot_register_users(client, seed_admin):
    # bootstrap a non-admin user via the admin
    admin_login = await _login(client, seed_admin["email"], seed_admin["password"])
    admin_token = admin_login.json()["access_token"]
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "employee@sentinelguard.ai",
            "password": "EmployeePass1!",
            "full_name": "Eve Employee",
            "role": "EMPLOYEE",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await _login(client, "employee@sentinelguard.ai", "EmployeePass1!")
    employee_token = login.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "hacker@sentinelguard.ai",
            "password": "Whatever123!",
            "full_name": "Bad Actor",
        },
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert resp.status_code == 403


async def test_me_endpoint_requires_valid_token(client, seed_admin):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401

    login = await _login(client, seed_admin["email"], seed_admin["password"])
    token = login.json()["access_token"]
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == seed_admin["email"]


async def test_refresh_token_rotation_and_reuse_is_blocked(client, seed_admin):
    login = await _login(client, seed_admin["email"], seed_admin["password"])
    old_refresh = login.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != old_refresh

    # Reusing the old (rotated-out) refresh token must now fail
    reuse_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse_resp.status_code == 401


async def test_logout_revokes_refresh_token(client, seed_admin):
    login = await _login(client, seed_admin["email"], seed_admin["password"])
    tokens = login.json()

    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert logout_resp.status_code == 204

    refresh_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_resp.status_code == 401


async def test_last_login_is_tracked(client, seed_admin):
    # Before login, last_login is empty
    resp_me = await client.post("/api/v1/auth/login", json={"email": seed_admin["email"], "password": seed_admin["password"]})
    assert resp_me.status_code == 200
    token = resp_me.json()["access_token"]

    resp_user = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp_user.status_code == 200
    assert resp_user.json()["last_login"] is not None


async def test_admin_can_toggle_user_status(client, seed_admin):
    admin_login = await client.post("/api/v1/auth/login", json={"email": seed_admin["email"], "password": seed_admin["password"]})
    admin_token = admin_login.json()["access_token"]

    # Register employee
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "temp-emp@sentinelguard.ai",
            "password": "EmployeePass1!",
            "full_name": "Temp Emp",
            "role": "EMPLOYEE",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    # Deactivate employee
    deact_resp = await client.post(
        f"/api/v1/auth/users/{user_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deact_resp.status_code == 200
    assert deact_resp.json()["is_active"] is False

    # Attempt login for deactivated user - should fail (403 or 401)
    login_resp = await client.post("/api/v1/auth/login", json={"email": "temp-emp@sentinelguard.ai", "password": "EmployeePass1!"})
    assert login_resp.status_code == 403

    # Reactivate employee
    act_resp = await client.post(
        f"/api/v1/auth/users/{user_id}/status",
        json={"is_active": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert act_resp.status_code == 200
    assert act_resp.json()["is_active"] is True

    # Attempt login again - should succeed
    login_resp2 = await client.post("/api/v1/auth/login", json={"email": "temp-emp@sentinelguard.ai", "password": "EmployeePass1!"})
    assert login_resp2.status_code == 200
