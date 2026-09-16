"""
Embedding service using SentenceTransformers.

Loads the embedding model once on demand and caches it, avoiding
re-loading latency. Provides methods for batch and single text embedding.
"""
from sentence_transformers import SentenceTransformer
from app.core.config import settings


class EmbeddingService:
    _model = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """Lazy-load and cache the SentenceTransformer model."""
        if cls._model is None:
            # Loads model from cache or downloads it locally on first call
            cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return cls._model

    def __init__(self):
        # Trigger lazy-load of model during init
        self.model = self.get_model()

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text claim or query."""
        if not text.strip():
            # Return zero vector of appropriate size (384 for all-MiniLM-L6-v2)
            return [0.0] * 384
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Batch embed a list of document text chunks."""
        if not texts:
            return []
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
