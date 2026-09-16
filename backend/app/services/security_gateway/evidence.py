"""
Evidence Engine.

Logs gateway inspection outputs, risk scores, and evidence details to the
Audit database.
"""
import uuid
from app.repositories.audit_log_repository import AuditLogRepository
from app.models.audit_log import AuditLog


class EvidenceEngine:
    def __init__(self, db_session):
        self.repo = AuditLogRepository(db_session)

    async def log_security_event(
        self,
        request_id: str,
        session_id: str | None,
        user_id: str,
        query: str,
        raw_response: str,
        inspection_result: dict
    ) -> AuditLog:
        """
        Log security inspection results to database.
        """
        u_id = uuid.UUID(str(user_id))
        req_id = uuid.UUID(str(request_id))
        
        s_id = None
        if session_id:
            s_id = uuid.UUID(str(session_id))

        audit = AuditLog(
            request_id=req_id,
            session_id=s_id,
            user_id=u_id,
            query=query,
            raw_response=raw_response,
            sanitized_response=inspection_result["response"],
            decision=inspection_result["decision"],
            risk_score=inspection_result["risk_score"],
            risk_level=inspection_result["risk_level"],
            evidence_json=inspection_result["security_summary"]
        )

        return await self.repo.save(audit)
