"""
Semantic Similarity Engine.

Segments LLM responses into sentences/claims, embeds them, and searches the
FAISS index. Collects evidence of leaks if similarity exceeds the threshold.
"""
import re
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.vector_store.index_manager import IndexManager


class SemanticSimilarityEngine:
    def __init__(self, threshold: float = 0.75):
        self.threshold = threshold
        self.embedding_service = EmbeddingService()
        self.store = IndexManager.get_store()

    def segment_text(self, text: str) -> list[str]:
        """
        Split text into sentences or claims, filtering empty strings.
        """
        # Split on sentence boundaries (. ! ?) followed by whitespace, or newlines
        sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
        return [s.strip() for s in sentences if s.strip()]

    def analyze(self, response_text: str) -> dict:
        """
        Analyze the generated response for semantic leakage.
        Returns a dictionary containing a score breakdown, findings, and evidence.
        """
        claims = self.segment_text(response_text)
        findings = []
        evidence = []
        max_score = 0.0

        for claim in claims:
            # Generate embedding
            claim_vector = self.embedding_service.embed_text(claim)
            
            # Search FAISS (retrieve top matching chunk)
            matches = self.store.search(claim_vector, top_k=1)
            
            if not matches:
                continue

            best_match = matches[0]
            score = best_match["score"]
            meta = best_match["metadata"]

            # Track highest similarity score across all claims
            if score > max_score:
                max_score = score

            # If similarity exceeds threshold, we have a leak!
            if score >= self.threshold:
                doc_name = meta.get("original_filename") or "Protected Document"
                finding = {
                    "claim": claim,
                    "score": score,
                    "matched_chunk_id": meta.get("chunk_id"),
                    "document_id": meta.get("document_id"),
                    "document_name": doc_name,
                    "classification": meta.get("classification")
                }
                findings.append(finding)
                
                # Append to evidence list matching the schema contract
                evidence.append({
                    "type": "SEMANTIC_SIMILARITY",
                    "severity": "HIGH" if score >= 0.85 else "MEDIUM",
                    "description": f"Claim resembles content in '{doc_name}' ({meta.get('classification')}) with {score:.2f} similarity.",
                    "details": finding
                })

        return {
            "max_score": max_score,
            "findings": findings,
            "evidence": evidence
        }
