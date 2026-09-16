"""
Permission-Aware Vector Chunk Retriever.

Searches the FAISS vector index and filters results on the fly based on the
requester's role, department, and document classification boundaries.
"""
from app.models.user import Role, User
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.vector_store.index_manager import IndexManager


class PermissionAwareRetriever:
    def __init__(self):
        self.store = IndexManager.get_store()
        self.embedding_service = EmbeddingService()

    def retrieve(self, query_text: str, user: User, top_k: int = 5) -> list[dict]:
        """
        Retrieve chunks matching query_text and filter by user permissions.
        """
        # Generate query embedding
        query_vector = self.embedding_service.embed_text(query_text)

        # Retrieve extra chunks to compensate for items filtered out by permissions
        raw_results = self.store.search(query_vector, top_k=top_k * 4)

        filtered_results = []
        for res in raw_results:
            meta = res["metadata"]

            # 1. Enforce Department boundary for non-admins
            if user.role not in (Role.ADMIN, Role.SUPER_ADMIN):
                # If document department doesn't match user department, drop it
                if meta.get("department") != user.department:
                    continue

            # 2. Enforce Classification restrictions by Role
            classification = meta.get("classification", "PUBLIC")
            if user.role == Role.EXTERNAL:
                # External users can ONLY retrieve PUBLIC documents
                if classification != "PUBLIC":
                    continue
            elif user.role == Role.EMPLOYEE:
                # Employees can retrieve PUBLIC and INTERNAL documents
                if classification in ("CONFIDENTIAL", "HIGHLY_CONFIDENTIAL", "RESTRICTED"):
                    continue
            elif user.role == Role.ANALYST:
                # Analysts can retrieve up to CONFIDENTIAL documents
                if classification in ("HIGHLY_CONFIDENTIAL", "RESTRICTED"):
                    continue

            filtered_results.append(res)
            if len(filtered_results) >= top_k:
                break

        return filtered_results
