"""In-memory store for testing and development."""

from __future__ import annotations

import re
import math
from typing import Any, Dict, List, Optional

from .base import MemoryStoreBase


class InMemoryStore(MemoryStoreBase):
    """In-memory memory store for testing and development.

    This backend stores documents in memory (Python dict) and provides
    TF-IDF-based search. Useful for testing without external dependencies.
    Data is lost when the process exits.
    """

    def __init__(self):
        self.backend = "in_memory"
        self.last_error: Optional[str] = None
        self._documents: Dict[str, Dict[str, Any]] = {}

    async def store(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a document in memory."""
        self._documents[doc_id] = {
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
        }
        return doc_id

    async def retrieve(
        self,
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        return self._documents.get(doc_id)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using TF-IDF similarity."""
        # Apply filters
        filtered_docs = []
        for doc in self._documents.values():
            if self._matches_filters(doc, filters):
                filtered_docs.append(doc)

        if not filtered_docs:
            return []

        # TF-IDF search
        docs = [doc["text"] for doc in filtered_docs]
        doc_tokens = [self._tokenize(text) for text in docs]
        idf = self._compute_idf(doc_tokens)
        doc_vectors = [self._tfidf(tokens, idf) for tokens in doc_tokens]

        query_tokens = self._tokenize(query)
        query_vec = self._tfidf(query_tokens, idf)

        scored: List[Dict[str, Any]] = []
        for doc, doc_vec in zip(filtered_docs, doc_vectors):
            score = self._cosine_similarity(query_vec, doc_vec)
            scored.append(
                {
                    "id": doc["id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "score": score,
                }
            )

        scored.sort(key=lambda item: (item["score"], item["id"]), reverse=True)
        return scored[:top_k]

    async def update(
        self,
        doc_id: str,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update an existing document."""
        if doc_id not in self._documents:
            return False

        if text is not None:
            self._documents[doc_id]["text"] = text

        if metadata is not None:
            # Merge metadata
            self._documents[doc_id]["metadata"] = {
                **self._documents[doc_id]["metadata"],
                **metadata,
            }

        return True

    async def delete(
        self,
        doc_id: str,
    ) -> bool:
        """Delete a document by ID."""
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False

    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count documents matching optional filters."""
        if not filters:
            return len(self._documents)

        count = 0
        for doc in self._documents.values():
            if self._matches_filters(doc, filters):
                count += 1
        return count

    async def health(self) -> Dict[str, Any]:
        """Check backend health and return diagnostics."""
        return {
            "backend": self.backend,
            "status": "healthy",
            "count": len(self._documents),
            "last_error": self.last_error,
        }

    async def clear(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Clear documents matching optional filters."""
        if not filters:
            count = len(self._documents)
            self._documents.clear()
            return count

        # Find matching documents
        to_delete = [
            doc_id for doc_id, doc in self._documents.items() if self._matches_filters(doc, filters)
        ]

        # Delete them
        for doc_id in to_delete:
            del self._documents[doc_id]

        return len(to_delete)

    # Helper methods

    def _matches_filters(self, doc: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        """Check if a document matches the given filters."""
        if not filters:
            return True

        metadata = doc.get("metadata", {})
        for key, value in filters.items():
            if metadata.get(key) != value:
                return False

        return True

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase alphanumeric tokens."""
        return re.findall(r"[a-z0-9]+", text.lower())

    def _compute_idf(self, docs_tokens: List[List[str]]) -> Dict[str, float]:
        """Compute IDF scores for all tokens in the corpus."""
        doc_count = len(docs_tokens)
        df: Dict[str, int] = {}
        for tokens in docs_tokens:
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1
        idf = {token: math.log((1 + doc_count) / (1 + freq)) + 1.0 for token, freq in df.items()}
        return idf

    def _tfidf(self, tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
        """Compute TF-IDF vector for a document."""
        if not tokens:
            return {}
        tf: Dict[str, float] = {}
        total = float(len(tokens))
        for token in tokens:
            tf[token] = tf.get(token, 0.0) + 1.0
        return {token: (count / total) * idf.get(token, 0.0) for token, count in tf.items()}

    def _cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        """Compute cosine similarity between two TF-IDF vectors."""
        if not vec_a or not vec_b:
            return 0.0
        dot = sum(value * vec_b.get(token, 0.0) for token, value in vec_a.items())
        norm_a = math.sqrt(sum(value * value for value in vec_a.values()))
        norm_b = math.sqrt(sum(value * value for value in vec_b.values()))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    # Backward compatibility aliases

    async def upsert_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Backward compatibility alias for store()."""
        return await self.store(doc_id, text, metadata)

    async def query_similar(
        self,
        query: str,
        top_k: int = 5,
        pattern_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Backward compatibility alias for search()."""
        filters = {"pattern_type": pattern_type} if pattern_type else None
        return await self.search(query, top_k, filters)
