"""
FAISS Vector Store Service.

Provides vector storage, incremental document additions, deletion, cosine
similarity searches, index rebuild from database, and persistence to disk.
"""
import json
import os
import uuid
from pathlib import Path
import numpy as np
import faiss

from app.core.config import settings
from app.models.document_chunk import DocumentChunk
from app.services.embeddings.embedding_service import EmbeddingService


class FAISSStore:
    def __init__(self, index_dir: str | None = None):
        self.index_dir = index_dir or settings.FAISS_INDEX_DIR
        self.index_path = Path(self.index_dir) / "index.faiss"
        self.metadata_path = Path(self.index_dir) / "metadata.json"
        
        # Dimension is 384 for all-MiniLM-L6-v2
        self.dimension = 384
        self.index = None
        self.metadata = {}  # maps string FAISS ID (integer as string) -> chunk info dict
        self.embedding_service = EmbeddingService()

        # Load existing index or create new one
        self.load_index()

    def _init_new_index(self) -> None:
        """Create a new IndexFlatIP (Inner Product) for cosine similarity."""
        # Using IndexFlatIP for normalized vectors gives cosine similarity
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = {}

    def save_index(self) -> None:
        """Persist index and metadata to disk."""
        Path(self.index_dir).mkdir(parents=True, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def load_index(self) -> None:
        """Load index and metadata from disk, fallback to new index if missing."""
        if self.index_path.exists() and self.metadata_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            except Exception:
                # Fallback on corrupt file
                self._init_new_index()
        else:
            self._init_new_index()

    def add_vectors(
        self,
        document_id: uuid.UUID,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]]
    ) -> None:
        """Add chunk vectors and map them to metadata."""
        if not chunks or not embeddings:
            return

        # Normalize embeddings to unit length for Cosine Similarity via Inner Product
        vectors = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)

        # Record start index in FAISS before adding
        start_id = self.index.ntotal
        self.index.add(vectors)

        # Map FAISS ID back to metadata
        for i, chunk in enumerate(chunks):
            faiss_id = str(start_id + i)
            self.metadata[faiss_id] = {
                "document_id": str(document_id),
                "chunk_id": str(chunk.id),
                "chunk_index": chunk.chunk_index,
                "original_filename": chunk.document.original_filename if hasattr(chunk, "document") and chunk.document else "Protected Document",
                "classification": chunk.document.classification.value if hasattr(chunk, "document") and chunk.document else "CONFIDENTIAL",
                "department": chunk.document.department if hasattr(chunk, "document") and chunk.document else "General",
                "page": chunk.page_number or 1,
                "content_hash": chunk.content_hash,
                "content": chunk.content
            }
        
        self.save_index()

    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        """
        Perform cosine similarity search.
        Returns a list of dicts: {"score": float, "metadata": dict}
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        # Format query vector
        query = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(query)

        # Search index
        scores, indices = self.index.search(query, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            faiss_id = str(idx)
            meta = self.metadata.get(faiss_id)
            if meta:
                # Cosine similarity is score (since vectors are L2-normalized)
                results.append({
                    "score": float(score),
                    "metadata": meta
                })
        
        return results

    def delete_document_vectors(self, document_id: uuid.UUID) -> None:
        """
        Remove all vectors associated with a document_id.
        Removes the metadata and drops IDs, saving updates to disk.
        """
        str_doc_id = str(document_id)
        
        # Identify FAISS IDs to keep
        ids_to_remove = []
        new_metadata = {}
        
        # We need to rebuild or filter. FAISS IndexFlatIP does not support easy arbitrary removal
        # unless we rebuild from remaining, or use index.remove_ids.
        # It is cleanest to recreate a new index and insert only the remaining vectors.
        remaining_vectors = []
        remaining_metadata_entries = []

        # Read all index vectors (reconstruct)
        for i in range(self.index.ntotal):
            faiss_id = str(i)
            meta = self.metadata.get(faiss_id)
            if meta and meta["document_id"] != str_doc_id:
                # Reconstruct vector
                vector = self.index.reconstruct(i)
                remaining_vectors.append(vector)
                remaining_metadata_entries.append(meta)

        # Reset index
        self._init_new_index()

        if remaining_vectors:
            vectors_np = np.array(remaining_vectors, dtype=np.float32)
            self.index.add(vectors_np)
            for i, meta in enumerate(remaining_metadata_entries):
                self.metadata[str(i)] = meta

        self.save_index()

    async def rebuild_index(self, db_session) -> None:
        """Rebuild vector index completely from database document chunks."""
        from sqlalchemy import select
        from app.models.document import Document
        from app.models.document_chunk import DocumentChunk
        
        # Fetch all ready documents
        stmt = select(Document).where(Document.status == "READY")
        result = await db_session.execute(stmt)
        documents = result.scalars().all()

        self._init_new_index()

        for doc in documents:
            # Fetch chunks for this document
            stmt_chunks = select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index)
            chunks_res = await db_session.execute(stmt_chunks)
            chunks = chunks_res.scalars().all()
            
            if not chunks:
                continue

            # Load document relation onto chunks for metadata parsing
            for chunk in chunks:
                chunk.document = doc

            texts = [c.content for c in chunks]
            embeddings = self.embedding_service.embed_documents(texts)
            self.add_vectors(doc.id, chunks, embeddings)

        self.save_index()
