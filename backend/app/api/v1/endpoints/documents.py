import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.document import Classification, Sensitivity
from app.models.user import Role, User
from app.schemas.document import DocumentOut
from app.services.document_service import DocumentService
from app.services.document_intelligence.document_processor import DocumentProcessor

router = APIRouter(prefix="/documents", tags=["Secure Knowledge Vault"])

_UPLOAD_ROLES = (Role.SUPER_ADMIN, Role.ADMIN, Role.ANALYST)


@router.post(
    "/upload",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form(...),
    owner: str = Form(...),
    classification: Classification = Form(...),
    sensitivity: Sensitivity = Form(...),
    version: str = Form("1.0"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*_UPLOAD_ROLES)),
):
    """
    Admin/Analyst-only.

    Uploads a document and stores metadata.

    Status:
        PENDING

    Actual extraction/chunking happens later through
    /documents/{document_id}/process.
    """
    service = DocumentService(db)

    return await service.upload(
        file=file,
        department=department,
        owner=owner,
        classification=classification,
        sensitivity=sensitivity,
        version=version,
        uploaded_by=current_user,
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    department: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DocumentService(db)

    return await service.list_documents(current_user, department)


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DocumentService(db)

    return await service.get(document_id, current_user)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            Role.SUPER_ADMIN,
            Role.ADMIN,
        )
    ),
):
    service = DocumentService(db)

    await service.delete(document_id, current_user)


# ---------------------------------------------------------------------
# Module 3 - Document Intelligence Engine
# ---------------------------------------------------------------------

@router.post(
    "/{document_id}/process",
    status_code=status.HTTP_200_OK,
    summary="Process uploaded document",
)
async def process_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            Role.SUPER_ADMIN,
            Role.ADMIN,
            Role.ANALYST,
        )
    ),
):
    """
    Process an uploaded document.

    Pipeline

        Upload
            ↓
        Extract Text
            ↓
        Clean Text
            ↓
        Chunk Text
            ↓
        Store Chunks
            ↓
        READY
    """

    processor = DocumentProcessor(db)

    result = await processor.process(document_id)

    return result