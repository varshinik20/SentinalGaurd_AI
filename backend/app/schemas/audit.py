"""
Pydantic schemas for Audit Logs.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    session_id: uuid.UUID | None
    user_id: uuid.UUID
    query: str
    raw_response: str
    sanitized_response: str
    decision: str
    risk_score: float
    risk_level: str
    evidence_json: dict | list
    created_at: datetime

    class Config:
        from_attributes = True
