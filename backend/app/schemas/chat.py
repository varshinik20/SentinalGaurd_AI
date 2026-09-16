"""
Chat API schemas.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4096)
    session_id: uuid.UUID | None = None
    provider: str = "offline"


class SecuritySummary(BaseModel):
    components: dict[str, float]
    policy: dict[str, str | None]
    evidence: list[dict]


class ChatResponse(BaseModel):
    response: str
    decision: str
    risk_score: float
    risk_level: str
    request_id: str
    security_summary: SecuritySummary


class ChatSessionOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    provider: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    sender: str
    content: str
    security_decision: str | None = None
    risk_score: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
