import pytest
import os
import uuid
import shutil
from pathlib import Path
from sqlalchemy import select

from app.services.embeddings.embedding_service import EmbeddingService
from app.services.vector_store.faiss_store import FAISSStore
from app.services.vector_store.index_manager import IndexManager
from app.models.document import Document, DocumentStatus, Classification, Sensitivity
from app.models.document_chunk import DocumentChunk
from app.core.config import settings


@pytest.fixture
def temp_index_dir(tmp_path):
    """Fixture to provide a clean temporary directory for FAISS index."""
    idx_dir = tmp_path / "faiss_test"
    idx_dir.mkdir()
    return str(idx_dir)


def test_embedding_service():
    service = EmbeddingService()
    emb = service.embed_text("Test query")
    assert len(emb) == 384
    assert isinstance(emb[0], float)

    batch_emb = service.embed_documents(["doc 1", "doc 2"])
    assert len(batch_emb) == 2
    assert len(batch_emb[0]) == 384


@pytest.mark.asyncio
async def test_faiss_store_lifecycle(temp_index_dir):
    store = FAISSStore(index_dir=temp_index_dir)
    
    # Assert initialized as empty
    assert store.index.ntotal == 0

    doc_id = uuid.uuid4()
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        chunk_index=0,
        content="Confidential financial report.",
        content_hash="hash1",
        page_number=1
    )
    
    # Seed embeddings
    service = EmbeddingService()
    emb = service.embed_documents([chunk.content])

    # Add to store
    store.add_vectors(doc_id, [chunk], emb)
    assert store.index.ntotal == 1
    assert "0" in store.metadata

    # Test Cosine Similarity Search
    q_emb = service.embed_text("financial report")
    search_res = store.search(q_emb, top_k=1)
    assert len(search_res) == 1
    assert search_res[0]["score"] > 0.0
    assert search_res[0]["metadata"]["content"] == chunk.content

    # Save and reload test
    store.save_index()
    assert os.path.exists(os.path.join(temp_index_dir, "index.faiss"))
    assert os.path.exists(os.path.join(temp_index_dir, "metadata.json"))

    store2 = FAISSStore(index_dir=temp_index_dir)
    assert store2.index.ntotal == 1
    assert store2.metadata["0"]["content"] == chunk.content

    # Delete test
    store2.delete_document_vectors(doc_id)
    assert store2.index.ntotal == 0
    assert "0" not in store2.metadata


@pytest.mark.asyncio
async def test_index_manager_rebuild(db_session, temp_index_dir, monkeypatch):
    # Override settings directory
    monkeypatch.setattr(settings, "FAISS_INDEX_DIR", temp_index_dir)
    
    # Add a ready document to DB
    doc = Document(
        id=uuid.uuid4(),
        filename="test.txt",
        original_filename="test.txt",
        file_type=".txt",
        file_size=100,
        file_hash="rebuild_hash",
        storage_path="dummy",
        content_type="text/plain",
        size_bytes=100,
        department="Finance",
        owner="Root",
        classification=Classification.INTERNAL,
        sensitivity=Sensitivity.MEDIUM,
        status=DocumentStatus.READY
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        chunk_index=0,
        content="This is active text to rebuild.",
        content_hash="rebuild_chunk_hash",
        page_number=1
    )
    db_session.add(chunk)
    await db_session.commit()

    manager = IndexManager()
    await manager.rebuild(db_session)

    # Verify rebuilt index
    store = manager.store
    assert store.index.ntotal == 1
    assert store.metadata["0"]["content"] == chunk.content
