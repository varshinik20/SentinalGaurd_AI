"""
Index Manager to coordinate FAISS index operations.

Maintains the FAISSStore singleton and provides operations to rebuild,
reload, and access the active vector index.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.vector_store.faiss_store import FAISSStore


class IndexManager:
    _store = None

    @classmethod
    def get_store(cls) -> FAISSStore:
        """Singleton accessor for the FAISS Store."""
        if cls._store is None:
            cls._store = FAISSStore()
        return cls._store

    def __init__(self):
        self.store = self.get_store()

    async def rebuild(self, db: AsyncSession) -> None:
        """Trigger complete index rebuild from database."""
        await self.store.rebuild_index(db)

    def reload(self) -> None:
        """Reload index and metadata from disk."""
        self.store.load_index()
