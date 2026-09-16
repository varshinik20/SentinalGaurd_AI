import io
import pytest
import uuid
from sqlalchemy import select

from app.models.user import Role
from app.models.document import Document, DocumentStatus, Classification, Sensitivity
from app.models.document_chunk import DocumentChunk
from app.services.rag.retriever import PermissionAwareRetriever
from app.services.vector_store.index_manager import IndexManager
from app.services.embeddings.embedding_service import EmbeddingService

pytestmark = pytest.mark.asyncio


async def _login(client, email, password):
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def test_chat_session_crud(client, seed_admin, monkeypatch, tmp_path):
    monkeypatch.setattr(settings := __import__("app.core.config").core.config.settings, "FAISS_INDEX_DIR", str(tmp_path))
    from app.services.vector_store.index_manager import IndexManager
    IndexManager._store = None
    token = await _login(client, seed_admin["email"], seed_admin["password"])
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a session by starting a chat
    resp = await client.post(
        "/api/v1/chat",
        json={"message": "What is the weather today?", "provider": "offline"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "response" in body
    assert body["decision"] == "ALLOW", f"Response body: {body}"

    # 2. List sessions
    list_resp = await client.get("/api/v1/chat/sessions", headers=headers)
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert len(sessions) > 0
    session_id = sessions[0]["id"]
    assert sessions[0]["provider"] == "offline"

    # 3. Retrieve specific session
    get_resp = await client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == session_id

    # 4. Delete session
    del_resp = await client.delete(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert del_resp.status_code == 204

    # 5. Retrieve after delete -> 404
    get_after = await client.get(f"/api/v1/chat/sessions/{session_id}", headers=headers)
    assert get_after.status_code == 404


async def test_permission_aware_retrieval(client, db_session, seed_admin, monkeypatch, tmp_path):
    # Setup clean FAISS test index
    monkeypatch.setattr(settings := __import__("app.core.config").core.config.settings, "FAISS_INDEX_DIR", str(tmp_path))
    
    # 1. Create Finance internal doc and HR confidential doc
    doc_fin = Document(
        id=uuid.uuid4(),
        filename="finance.txt",
        original_filename="finance.txt",
        file_type=".txt",
        file_size=10,
        file_hash="fin_hash",
        storage_path="dummy",
        content_type="text/plain",
        size_bytes=10,
        department="Finance",
        owner="Finance Lead",
        classification=Classification.INTERNAL,
        sensitivity=Sensitivity.MEDIUM,
        status=DocumentStatus.READY
    )
    db_session.add(doc_fin)
    await db_session.commit()

    chunk_fin = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_fin.id,
        chunk_index=0,
        content="Finance budget allocation details.",
        content_hash="fin_c_hash",
        page_number=1
    )
    db_session.add(chunk_fin)
    await db_session.commit()

    doc_hr = Document(
        id=uuid.uuid4(),
        filename="hr.txt",
        original_filename="hr.txt",
        file_type=".txt",
        file_size=10,
        file_hash="hr_hash",
        storage_path="dummy",
        content_type="text/plain",
        size_bytes=10,
        department="HR",
        owner="HR Lead",
        classification=Classification.CONFIDENTIAL,
        sensitivity=Sensitivity.HIGH,
        status=DocumentStatus.READY
    )
    db_session.add(doc_hr)
    await db_session.commit()

    chunk_hr = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_hr.id,
        chunk_index=0,
        content="HR employee performance records.",
        content_hash="hr_c_hash",
        page_number=1
    )
    db_session.add(chunk_hr)
    await db_session.commit()

    # Rebuild FAISS index
    chunk_fin.document = doc_fin
    chunk_hr.document = doc_hr
    
    store = IndexManager.get_store()
    store._init_new_index()
    embedder = EmbeddingService()
    
    store.add_vectors(doc_fin.id, [chunk_fin], embedder.embed_documents([chunk_fin.content]))
    store.add_vectors(doc_hr.id, [chunk_hr], embedder.embed_documents([chunk_hr.content]))

    # Register HR Employee
    admin_token = await _login(client, seed_admin["email"], seed_admin["password"])
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "hr-worker@sentinelguard.ai",
            "password": "HRWorkerPass1!",
            "full_name": "HR Worker",
            "role": "EMPLOYEE",
            "department": "HR",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    
    # Retrieve user from DB
    from app.models.user import User
    res_user = await db_session.execute(select(User).where(User.email == "hr-worker@sentinelguard.ai"))
    hr_user = res_user.scalar_one()

    # Test retriever
    retriever = PermissionAwareRetriever()
    
    # HR worker queries: should NOT see finance chunk (different department)
    hr_res = retriever.retrieve("budget and performance", hr_user)
    assert len(hr_res) == 0  # finance filtered by dept, HR filtered because EMPLOYEE cannot access CONFIDENTIAL
