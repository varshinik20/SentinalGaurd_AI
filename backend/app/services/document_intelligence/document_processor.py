"""
Document processing service.

Coordinates the complete Document Intelligence pipeline.

Pipeline:
Document
    ↓
Extract Text
    ↓
Clean Text
    ↓
Chunk Text
    ↓
Save Chunks
    ↓
Update Document Status
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentStatus
from app.repositories.document_repository import DocumentRepository
from app.services.document_intelligence.text_cleaner import TextCleaner
from app.services.document_intelligence.text_chunker import TextChunker
from app.services.document_intelligence.text_extractor import TextExtractor


class DocumentProcessor:
    """Coordinates document extraction, cleaning and chunking."""

    def __init__(self, db: AsyncSession):
        self.db = db

        self.repository = DocumentRepository(db)

        self.extractor = TextExtractor()
        self.cleaner = TextCleaner()
        self.chunker = TextChunker()

    async def process(self, document_id):
        """
        Process a document from upload to chunks.

        Workflow:
            PENDING
                ↓
            PROCESSING
                ↓
            READY
        """

        document = await self.repository.get_by_id(document_id)

        if document is None:
            raise ValueError("Document not found.")

        try:
            # Mark document as processing
            await self.repository.update_status(
                document.id,
                DocumentStatus.PROCESSING,
            )

            # Extract text page-by-page
            pages = self.extractor.extract_pages(document.storage_path)

            all_chunks = []
            for page_num, raw_text in pages:
                # Clean extracted text
                cleaned_text = self.cleaner.clean(raw_text)

                # Split into chunks
                page_chunks = self.chunker.chunk(cleaned_text)

                for chunk in page_chunks:
                    all_chunks.append({
                        "content": chunk,
                        "page_number": page_num,
                        "metadata": {
                            "source_type": document.file_type,
                            "classification": document.classification.value,
                            "department": document.department
                        }
                    })

            # Remove previous chunks if any
            await self.repository.delete_chunks(document.id)

            # Save new chunks
            await self.repository.save_chunks(
                document.id,
                all_chunks,
            )

            # --- MODULE 4 INTEGRATION: Add to FAISS Vector Store ---
            # Retrieve saved chunks to get their database IDs
            db_chunks = await self.repository.get_chunks(document.id)
            for c in db_chunks:
                c.document = document

            from app.services.embeddings.embedding_service import EmbeddingService
            from app.services.vector_store.index_manager import IndexManager

            embedder = EmbeddingService()
            index_manager = IndexManager()

            chunk_texts = [c.content for c in db_chunks]
            embeddings = embedder.embed_documents(chunk_texts)
            index_manager.store.add_vectors(document.id, db_chunks, embeddings)
            # -------------------------------------------------------

            # Mark as ready
            await self.repository.update_status(
                document.id,
                DocumentStatus.READY,
            )

            return {
                "document_id": str(document.id),
                "status": DocumentStatus.READY.value,
                "chunks_created": len(all_chunks),
            }

        except Exception as exc:

            await self.repository.update_status(
                document.id,
                DocumentStatus.FAILED,
                failure_reason=str(exc),
            )

            raise