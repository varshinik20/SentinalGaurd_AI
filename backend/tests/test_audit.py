import pytest
import uuid
from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.chat import ChatResponse

pytestmark = pytest.mark.asyncio


async def test_evidence_engine_pii_masking(db_session):
    from app.models.user import User, Role
    admin_user = User(
        id=uuid.uuid4(),
        email="audit_tester@sentinelguard.ai",
        hashed_password="dummy",
        full_name="Audit Tester",
        role=Role.ADMIN,
        department="Finance"
    )
    db_session.add(admin_user)
    await db_session.commit()

    # Setup repo
    repo = AuditLogRepository(db_session)

    # 1. Create audit log containing credit card number (PII)
    raw_response = "The balance can be paid to card 4111-1111-1111-1111."
    audit = AuditLog(
        request_id=uuid.uuid4(),
        session_id=None,
        user_id=admin_user.id,
        query="What is the payment card?",
        raw_response=raw_response,
        sanitized_response=raw_response,
        decision="ALLOW",
        risk_score=0.1,
        risk_level="LOW",
        evidence_json={}
    )

    saved = await repo.save(audit)
    
    # Assert credit card is masked inside database audit records
    assert "[MASKED_CREDIT_CARD]" in saved.raw_response
    assert "4111-1111-1111-1111" not in saved.raw_response


async def test_audit_logs_rbac_endpoints(client, seed_admin):
    from tests.test_rag import _login

    # 1. Admin login -> HTTP 200
    admin_token = await _login(client, seed_admin["email"], seed_admin["password"])
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Register analyst user dynamically
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "analyst@sentinelguard.ai",
            "password": "AnalystPass1!",
            "full_name": "Jane Analyst",
            "role": "ANALYST",
            "department": "Finance",
        },
        headers=headers_admin
    )
    assert reg_resp.status_code == 201

    resp_admin = await client.get("/api/v1/audit/logs", headers=headers_admin)
    assert resp_admin.status_code == 200
    assert isinstance(resp_admin.json(), list)

    # 2. Employee login -> HTTP 403 Forbidden
    emp_token = await _login(client, "analyst@sentinelguard.ai", "AnalystPass1!")
    headers_emp = {"Authorization": f"Bearer {emp_token}"}
    
    resp_emp = await client.get("/api/v1/audit/logs", headers=headers_emp)
    assert resp_emp.status_code == 403
