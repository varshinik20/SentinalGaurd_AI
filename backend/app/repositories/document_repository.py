import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Module 2 - Secure Knowledge Vault
    # ------------------------------------------------------------------

    async def create(self, document: Document) -> Document:
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_by_hash(self, file_hash: str) -> Document | None:
        result = await self.db.execute(
            select(Document).where(Document.file_hash == file_hash)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        department: str | None = None,
    ) -> list[Document]:

        stmt = select(Document).order_by(Document.uploaded_at.desc())

        if department:
            stmt = stmt.where(Document.department == department)

        result = await self.db.execute(stmt)

        return list(result.scalars().all())

    async def delete(self, document: Document) -> None:
        await self.db.delete(document)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Module 3 - Document Intelligence Engine
    # ------------------------------------------------------------------

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        failure_reason: str | None = None,
    ) -> Document | None:

        document = await self.get_by_id(document_id)

        if document is None:
            return None

        document.status = status
        document.failure_reason = failure_reason

        await self.db.commit()
        await self.db.refresh(document)

        return document

    async def delete_chunks(
        self,
        document_id: uuid.UUID,
    ) -> None:

        stmt = delete(DocumentChunk).where(
            DocumentChunk.document_id == document_id
        )

        await self.db.execute(stmt)
        await self.db.commit()

    async def save_chunks(
        self,
        document_id: uuid.UUID,
        chunks: list[str] | list[dict],
    ) -> None:
        import hashlib

        chunk_objects = []

        for index, chunk in enumerate(chunks):
            if isinstance(chunk, dict):
                content = chunk["content"]
                page_number = chunk.get("page_number")
                metadata_json = chunk.get("metadata")
            else:
                content = chunk
                page_number = None
                metadata_json = None

            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

            chunk_objects.append(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=index,
                    content=content,
                    content_hash=content_hash,
                    page_number=page_number,
                    metadata_json=metadata_json,
                )
            )

        self.db.add_all(chunk_objects)

        await self.db.commit()

    async def get_chunks(
        self,
        document_id: uuid.UUID,
    ) -> list[DocumentChunk]:

        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )

        return list(result.scalars().all())

    async def chunk_count(
        self,
        document_id: uuid.UUID,
    ) -> int:

        chunks = await self.get_chunks(document_id)

        return len(chunks)