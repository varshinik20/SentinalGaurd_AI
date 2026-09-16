"""
AuditLog Repository.

Handles storing, searching, and securing security gateway audit records.
Ensures raw text values are sanitized/masked before database insertion.
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
from app.services.security_gateway.sensitive_information import SensitiveInformationAnalyzer


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sensitive_analyzer = SensitiveInformationAnalyzer()

    async def save(self, audit: AuditLog) -> AuditLog:
        """Mask sensitive values in the audit record before committing."""
        audit.query = self.sensitive_analyzer.analyze(audit.query)["masked_text"]
        audit.raw_response = self.sensitive_analyzer.analyze(audit.raw_response)["masked_text"]
        audit.sanitized_response = self.sensitive_analyzer.analyze(audit.sanitized_response)["masked_text"]
        
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(audit)
        return audit

    async def search(
        self,
        skip: int = 0,
        limit: int = 100,
        decision: str | None = None,
        risk_level: str | None = None
    ) -> list[AuditLog]:
        """Search and filter security logs for admin dashboards."""
        query = select(AuditLog)
        
        if decision:
            query = query.where(AuditLog.decision == decision)
        if risk_level:
            query = query.where(AuditLog.risk_level == risk_level)

        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
