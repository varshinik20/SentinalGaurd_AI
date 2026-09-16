"""documents table

Revision ID: 0002_documents
Revises: 0001_initial_auth_schema
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_documents"
down_revision = "0001_initial_auth_schema"
branch_labels = None
depends_on = None

classification_enum = postgresql.ENUM(
    "PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", name="document_classification"
)
sensitivity_enum = postgresql.ENUM(
    "LOW", "MEDIUM", "HIGH", "CRITICAL", name="document_sensitivity"
)
status_enum = postgresql.ENUM(
    "PENDING", "PROCESSING", "READY", "FAILED", name="document_status"
)


def upgrade() -> None:
    bind = op.get_bind()
    classification_enum.create(bind, checkfirst=True)
    sensitivity_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column(
            "classification",
            postgresql.ENUM(
                "PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED",
                name="document_classification", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "sensitivity",
            postgresql.ENUM(
                "LOW", "MEDIUM", "HIGH", "CRITICAL",
                name="document_sensitivity", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("version", sa.String(length=20), nullable=False, server_default="1.0"),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING", "PROCESSING", "READY", "FAILED",
                name="document_status", create_type=False,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("failure_reason", sa.String(length=1000), nullable=True),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_department", "documents", ["department"])
    op.create_index("ix_documents_status", "documents", ["status"])


def downgrade() -> None:
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_department", table_name="documents")
    op.drop_table("documents")
    status_enum.drop(op.get_bind(), checkfirst=True)
    sensitivity_enum.drop(op.get_bind(), checkfirst=True)
    classification_enum.drop(op.get_bind(), checkfirst=True)
