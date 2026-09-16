"""
Audit Logs API Router.

Provides search and filter endpoints for the SentinelGuard AI security gateway
audit records, protected by role-based access checks.
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User, Role
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.audit import AuditLogResponse

router = APIRouter()


@router.get("/logs", response_model=list[AuditLogResponse])
async def search_audit_logs(
    skip: int = 0,
    limit: int = 100,
    decision: str | None = None,
    risk_level: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Retrieve security gateway audit logs. Requires Admin privilege.
    """
    # Enforce role-based access control (RBAC)
    user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if user_role not in ("ADMIN", "SUPER_ADMIN") and current_user.role not in (Role.ADMIN, Role.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin role privilege is required to access audit logs."
        )

    repo = AuditLogRepository(db)
    logs = await repo.search(
        skip=skip,
        limit=limit,
        decision=decision,
        risk_level=risk_level
    )
    return logs
