import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.document import Classification, DocumentStatus, Sensitivity


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    file_hash: str
    storage_path: str
    content_type: str
    size_bytes: int
    department: str
    owner: str
    classification: Classification
    sensitivity: Sensitivity
    version: str
    status: DocumentStatus
    failure_reason: str | None
    uploaded_by: uuid.UUID | None
    owner_id: uuid.UUID | None
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
