"""
Document chunking service.

Splits cleaned text into overlapping chunks suitable for semantic embedding.

This module does NOT generate embeddings.
It simply prepares high-quality chunks for Module 4.
"""

from typing import List
from transformers import AutoTokenizer
import logging

logger = logging.getLogger(__name__)


class TextChunker:
    """
    Splits cleaned text into overlapping token-based chunks.
    """

    def __init__(
        self,
        chunk_size: int = 250,
        chunk_overlap: int = 50,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        try:
            # Load tokenizer locally (will read from huggingface cache or download once)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        except Exception as e:
            logger.warning(f"Could not load AutoTokenizer from {model_name}: {e}. Falling back to word-based chunker.")
            self.tokenizer = None

    def chunk(self, text: str) -> List[str]:
        """
        Split cleaned text into overlapping token-based chunks.

        Args:
            text: Cleaned document text.

        Returns:
            List of text chunks.
        """
        if not text.strip():
            return []

        # Fallback to word-based chunking if tokenizer isn't available
        if self.tokenizer is None:
            words = text.split()
            chunks = []
            start = 0
            while start < len(words):
                end = min(start + self.chunk_size, len(words))
                chunks.append(" ".join(words[start:end]))
                if end == len(words):
                    break
                start = end - self.chunk_overlap
            return chunks

        # Token-based chunking using the HF tokenizer
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens, clean_up_tokenization_spaces=True)
            chunks.append(chunk_text)
            if end == len(tokens):
                break
            start = end - self.chunk_overlap

        return chunks