import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Classification, Document, Sensitivity
from app.models.user import Role, User
from app.repositories.document_repository import DocumentRepository
from app.utils.file_storage import delete_document_files, save_upload, validate_upload


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DocumentRepository(db)

    async def upload(
        self,
        file: UploadFile,
        department: str,
        owner: str,
        classification: Classification,
        sensitivity: Sensitivity,
        version: str,
        uploaded_by: User,
    ) -> Document:
        # Enforce department restriction for non-admins
        if uploaded_by.role not in (Role.ADMIN, Role.SUPER_ADMIN):
            if uploaded_by.department != department:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot upload document to a different department.",
                )

        filename = file.filename
        if not filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty filename.",
            )

        # Path traversal prevention
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path traversal detected in filename.",
            )

        sanitized_filename = os.path.basename(filename)
        ext = validate_upload(file)
        document_id = uuid.uuid4()
        storage_path, size_bytes, file_hash = await save_upload(file, document_id, ext)

        # Check for duplicate documents
        existing = await self.repo.get_by_hash(file_hash)
        if existing:
            delete_document_files(document_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A document with this content already exists.",
            )

        document = Document(
            id=document_id,
            filename=sanitized_filename,
            original_filename=filename,
            file_type=ext,
            file_size=size_bytes,
            file_hash=file_hash,
            storage_path=storage_path,
            content_type=file.content_type,
            size_bytes=size_bytes,
            department=department,
            owner=owner,
            classification=classification,
            sensitivity=sensitivity,
            version=version,
            uploaded_by=uploaded_by.id,
            owner_id=uploaded_by.id,
        )
        return await self.repo.create(document)

    async def list_documents(self, user: User, department: str | None = None) -> list[Document]:
        # Enforce department restriction for non-admins
        if user.role not in (Role.ADMIN, Role.SUPER_ADMIN):
            return await self.repo.list_all(department=user.department)
        return await self.repo.list_all(department)

    async def get(self, document_id: uuid.UUID, user: User) -> Document:
        document = await self.repo.get_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found."
            )
        # Enforce department restriction for non-admins
        if user.role not in (Role.ADMIN, Role.SUPER_ADMIN):
            if document.department != user.department:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. Document belongs to another department.",
                )
        return document

    async def delete(self, document_id: uuid.UUID, user: User) -> None:
        document = await self.get(document_id, user)
        # Delete vectors from FAISS Store
        from app.services.vector_store.index_manager import IndexManager
        IndexManager.get_store().delete_document_vectors(document.id)
        
        delete_document_files(document.id)
        await self.repo.delete(document)
