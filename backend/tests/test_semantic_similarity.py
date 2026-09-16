import pytest
import uuid
from app.services.security_gateway.semantic_similarity import SemanticSimilarityEngine
from app.services.vector_store.index_manager import IndexManager
from app.services.embeddings.embedding_service import EmbeddingService
from app.models.document import Document, DocumentStatus, Classification, Sensitivity
from app.models.document_chunk import DocumentChunk
from app.core.config import settings

@pytest.fixture
def temp_index_dir(tmp_path):
    idx_dir = tmp_path / "faiss_test"
    idx_dir.mkdir()
    return str(idx_dir)


def test_claim_segmentation():
    engine = SemanticSimilarityEngine()
    text = "Sentence one. Sentence two! Sentence three? And another one."
    claims = engine.segment_text(text)
    assert len(claims) == 4
    assert claims[0] == "Sentence one."
    assert claims[1] == "Sentence two!"


@pytest.mark.asyncio
async def test_semantic_similarity_analysis(db_session, temp_index_dir, monkeypatch):
    # Override settings directory
    monkeypatch.setattr(settings := __import__("app.core.config").core.config.settings, "FAISS_INDEX_DIR", temp_index_dir)
    
    # 1. Create a dummy document chunk in database
    doc = Document(
        id=uuid.uuid4(),
        filename="project_omega.txt",
        original_filename="project_omega.txt",
        file_type=".txt",
        file_size=100,
        file_hash="omega_hash",
        storage_path="dummy",
        content_type="text/plain",
        size_bytes=100,
        department="Engineering",
        owner="Developer",
        classification=Classification.HIGHLY_CONFIDENTIAL,
        sensitivity=Sensitivity.HIGH,
        status=DocumentStatus.READY
    )
    db_session.add(doc)
    await db_session.commit()

    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        chunk_index=0,
        content="Project Omega is our classified next-generation cloud infrastructure.",
        content_hash="omega_chunk_hash",
        page_number=1
    )
    db_session.add(chunk)
    await db_session.commit()

    # Seed FAISS store
    chunk.document = doc
    store = IndexManager.get_store()
    store._init_new_index()
    
    embedder = EmbeddingService()
    store.add_vectors(doc.id, [chunk], embedder.embed_documents([chunk.content]))

    # 2. Analyze a text containing a semantic match (high similarity)
    engine = SemanticSimilarityEngine(threshold=0.70)
    response_text = "Today we deployed Project Omega, our next-generation cloud database."
    results = engine.analyze(response_text)
    
    assert results["max_score"] >= 0.70
    assert len(results["findings"]) == 1
    assert results["findings"][0]["document_name"] == "project_omega.txt"
    assert results["findings"][0]["classification"] == "HIGHLY_CONFIDENTIAL"
    assert len(results["evidence"]) == 1
    assert results["evidence"][0]["type"] == "SEMANTIC_SIMILARITY"

    # 3. Analyze a completely unrelated response
    unrelated_text = "The quick brown fox jumps over the lazy dog."
    results_unrelated = engine.analyze(unrelated_text)
    assert results_unrelated["max_score"] < 0.60
    assert len(results_unrelated["findings"]) == 0
    assert len(results_unrelated["evidence"]) == 0
