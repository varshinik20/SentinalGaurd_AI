"""
AuditLog database model.

Stores detailed security gateway inspection audits, classification events,
and risk scores. Includes automatic database schema mappings.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    raw_response: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    sanitized_response: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(
        String(20),  # "ALLOW", "WARN", "REWRITE", "BLOCK", "HUMAN_REVIEW"
        nullable=False,
    )
    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
        nullable=False,
    )
    evidence_json: Mapped[dict | list] = mapped_column(
        JSON,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
    )

    user = relationship("User", backref="audit_logs")
    session = relationship("ChatSession", backref="audit_logs")
