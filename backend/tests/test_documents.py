import io

import pytest

pytestmark = pytest.mark.asyncio


async def _login(client, email, password):
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def _auth_headers(client, seed_admin):
    token = await _login(client, seed_admin["email"], seed_admin["password"])
    return {"Authorization": f"Bearer {token}"}


def _upload_fields(**overrides):
    fields = {
        "department": "Finance",
        "owner": "Jane Doe",
        "classification": "CONFIDENTIAL",
        "sensitivity": "HIGH",
        "version": "1.0",
    }
    fields.update(overrides)
    return fields


async def test_admin_can_upload_txt_document(client, seed_admin):
    headers = await _auth_headers(client, seed_admin)
    file_content = b"Employee salary bands are strictly confidential."

    resp = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data=_upload_fields(),
        files={"file": ("policy.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "policy.txt"
    assert body["status"] == "PENDING"
    assert body["department"] == "Finance"
    assert body["size_bytes"] == len(file_content)


async def test_upload_rejects_disallowed_file_type(client, seed_admin):
    headers = await _auth_headers(client, seed_admin)
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data=_upload_fields(),
        files={"file": ("virus.exe", io.BytesIO(b"MZ..."), "application/x-msdownload")},
    )
    assert resp.status_code == 400


async def test_employee_cannot_upload_document(client, seed_admin):
    admin_headers = await _auth_headers(client, seed_admin)
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "employee@sentinelguard.ai",
            "password": "EmployeePass1!",
            "full_name": "Eve Employee",
            "role": "EMPLOYEE",
            "department": "Finance",
        },
        headers=admin_headers,
    )
    employee_token = await _login(client, "employee@sentinelguard.ai", "EmployeePass1!")

    resp = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {employee_token}"},
        data=_upload_fields(),
        files={"file": ("policy.txt", io.BytesIO(b"data"), "text/plain")},
    )
    assert resp.status_code == 403


async def test_list_and_get_and_delete_document(client, seed_admin):
    headers = await _auth_headers(client, seed_admin)
    upload_resp = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data=_upload_fields(department="Legal"),
        files={"file": ("contract.txt", io.BytesIO(b"Confidential contract text"), "text/plain")},
    )
    document_id = upload_resp.json()["id"]

    list_resp = await client.get("/api/v1/documents", headers=headers)
    assert list_resp.status_code == 200
    assert any(d["id"] == document_id for d in list_resp.json())

    filtered_resp = await client.get(
        "/api/v1/documents", params={"department": "Legal"}, headers=headers
    )
    assert all(d["department"] == "Legal" for d in filtered_resp.json())

    get_resp = await client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == document_id

    delete_resp = await client.delete(f"/api/v1/documents/{document_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_after_delete = await client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert get_after_delete.status_code == 404


async def test_get_nonexistent_document_returns_404(client, seed_admin):
    headers = await _auth_headers(client, seed_admin)
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/v1/documents/{fake_id}", headers=headers)
    assert resp.status_code == 404


async def test_upload_requires_authentication(client):
    resp = await client.post(
        "/api/v1/documents/upload",
        data=_upload_fields(),
        files={"file": ("policy.txt", io.BytesIO(b"data"), "text/plain")},
    )
    assert resp.status_code == 401


async def test_upload_csv_and_xlsx_allowed(client, seed_admin):
    headers = await _auth_headers(client, seed_admin)
    
    # Upload CSV
    csv_resp = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data=_upload_fields(department="Finance"),
        files={"file": ("data.csv", io.BytesIO(b"col1,col2\nval1,val2"), "text/csv")},
    )
    assert csv_resp.status_code == 201
    assert csv_resp.json()["filename"] == "data.csv"

    # Upload XLSX
    xlsx_resp = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data=_upload_fields(department="Finance"),
        files={"file": ("spreadsheet.xlsx", io.BytesIO(b"dummy binary content xlsx"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert xlsx_resp.status_code == 201
    assert xlsx_resp.json()["filename"] == "spreadsheet.xlsx"


async def test_upload_rejects_path_traversal(client, seed_admin):
    headers = await _auth_headers(client, seed_admin)
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data=_upload_fields(),
        files={"file": ("../../malicious.txt", io.BytesIO(b"bad"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "Path traversal" in resp.json()["detail"]


async def test_upload_rejects_duplicate_content(client, seed_admin):
    headers = await _auth_headers(client, seed_admin)
    content = b"Unique secret doc content"

    resp1 = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data=_upload_fields(),
        files={"file": ("doc1.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data=_upload_fields(),
        files={"file": ("doc2.txt", io.BytesIO(content), "text/plain")},
    )
    assert resp2.status_code == 409


async def test_department_access_restrictions(client, seed_admin):
    admin_headers = await _auth_headers(client, seed_admin)

    # Register HR employee
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "hr-emp@sentinelguard.ai",
            "password": "HREmployeePass1!",
            "full_name": "HR Employee",
            "role": "EMPLOYEE",
            "department": "HR",
        },
        headers=admin_headers,
    )
    hr_token = await _login(client, "hr-emp@sentinelguard.ai", "HREmployeePass1!")
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    # Upload Finance document as Admin
    finance_upload = await client.post(
        "/api/v1/documents/upload",
        headers=admin_headers,
        data=_upload_fields(department="Finance"),
        files={"file": ("finance_leak.txt", io.BytesIO(b"finance data"), "text/plain")},
    )
    assert finance_upload.status_code == 201
    finance_doc_id = finance_upload.json()["id"]

    # HR employee attempts to get Finance document -> 403
    get_resp = await client.get(f"/api/v1/documents/{finance_doc_id}", headers=hr_headers)
    assert get_resp.status_code == 403

    # HR employee lists documents -> should not see Finance document
    list_resp = await client.get("/api/v1/documents", headers=hr_headers)
    assert list_resp.status_code == 200
    assert not any(d["id"] == finance_doc_id for d in list_resp.json())
