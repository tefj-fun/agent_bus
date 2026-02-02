"""Postgres-backed memory store with TF-IDF search."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, Iterable, List, Optional

import asyncpg

from .base import MemoryStoreBase


class PostgresMemoryStore(MemoryStoreBase):
    """Store and query project memory using Postgres persistence with TF-IDF search.

    This backend stores documents in the memory_patterns table and performs
    TF-IDF-based similarity search for queries. Suitable for keyword-based
    retrieval and when vector embeddings are not needed.
    """

    def __init__(self, db_pool: asyncpg.Pool, pattern_type_default: str = "document"):
        self.db_pool = db_pool
        self.pattern_type_default = pattern_type_default
        self.backend = "postgres_tfidf"
        self.last_error: Optional[str] = None

    async def store(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store or update a document in Postgres."""
        record_metadata = metadata or {}
        pattern_type = record_metadata.get("pattern_type", self.pattern_type_default)

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memory_patterns (
                    id, pattern_type, content, metadata, created_at, last_used_at
                )
                VALUES ($1, $2, $3, $4::jsonb, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                SET pattern_type = $2,
                    content = $3,
                    metadata = $4::jsonb,
                    last_used_at = NOW()
                """,
                doc_id,
                pattern_type,
                text,
                json.dumps(record_metadata),
            )
        return doc_id

    async def retrieve(
        self,
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, content, metadata, pattern_type
                FROM memory_patterns
                WHERE id = $1
                """,
                doc_id,
            )

        if not row:
            return None

        return {
            "id": row["id"],
            "text": row["content"],
            "metadata": row["metadata"] or {},
            "pattern_type": row.get("pattern_type"),
        }

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using TF-IDF similarity.

        Filters support:
        - pattern_type: Filter by pattern type
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content, metadata, pattern_type
                FROM memory_patterns
                """
            )

        records = [dict(row) for row in rows]
        if not records:
            return []

        # Apply filters
        pattern_type = filters.get("pattern_type") if filters else None
        filtered_rows = [
            row
            for row in records
            if pattern_type is None or row.get("pattern_type") == pattern_type
        ]
        if not filtered_rows:
            return []

        # TF-IDF search
        docs = [row.get("content", "") for row in filtered_rows]
        doc_tokens = [self._tokenize(text) for text in docs]
        idf = self._compute_idf(doc_tokens)
        doc_vectors = [self._tfidf(tokens, idf) for tokens in doc_tokens]

        query_tokens = self._tokenize(query)
        query_vec = self._tfidf(query_tokens, idf)

        scored: List[Dict[str, Any]] = []
        for row, doc_vec in zip(filtered_rows, doc_vectors):
            score = self._cosine_similarity(query_vec, doc_vec)
            scored.append(
                {
                    "id": row.get("id"),
                    "text": row.get("content", ""),
                    "metadata": row.get("metadata") or {},
                    "score": score,
                }
            )

        scored.sort(key=lambda item: (item.get("score", 0.0), item.get("id", "")), reverse=True)
        return scored[:top_k]

    async def update(
        self,
        doc_id: str,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update an existing document."""
        # First check if document exists
        existing = await self.retrieve(doc_id)
        if not existing:
            return False

        # Prepare updates
        if text is None:
            text = existing["text"]

        if metadata is None:
            new_metadata = existing["metadata"]
        else:
            # Merge metadata
            new_metadata = {**existing["metadata"], **metadata}

        pattern_type = new_metadata.get("pattern_type", self.pattern_type_default)

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE memory_patterns
                SET content = $2,
                    metadata = $3::jsonb,
                    pattern_type = $4,
                    last_used_at = NOW()
                WHERE id = $1
                """,
                doc_id,
                text,
                json.dumps(new_metadata),
                pattern_type,
            )

        return True

    async def delete(
        self,
        doc_id: str,
    ) -> bool:
        """Delete a document by ID."""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM memory_patterns
                WHERE id = $1
                """,
                doc_id,
            )

        # result is like "DELETE 1" or "DELETE 0"
        deleted = int(result.split()[-1]) if result else 0
        return deleted > 0

    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count documents matching optional filters."""
        pattern_type = filters.get("pattern_type") if filters else None

        async with self.db_pool.acquire() as conn:
            if pattern_type:
                count = await conn.fetchval(
                    "SELECT COUNT(1) FROM memory_patterns WHERE pattern_type = $1",
                    pattern_type,
                )
            else:
                count = await conn.fetchval("SELECT COUNT(1) FROM memory_patterns")

        return int(count or 0)

    async def health(self) -> Dict[str, Any]:
        """Check backend health and return diagnostics."""
        try:
            count = await self.count()
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "backend": self.backend,
                "status": "error",
                "count": 0,
                "last_error": self.last_error,
            }

        return {
            "backend": self.backend,
            "status": "healthy",
            "count": count,
            "last_error": self.last_error,
        }

    async def clear(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Clear documents matching optional filters."""
        pattern_type = filters.get("pattern_type") if filters else None

        async with self.db_pool.acquire() as conn:
            if pattern_type:
                result = await conn.execute(
                    "DELETE FROM memory_patterns WHERE pattern_type = $1",
                    pattern_type,
                )
            else:
                result = await conn.execute("DELETE FROM memory_patterns")

        deleted = int(result.split()[-1]) if result else 0
        return deleted

    # TF-IDF helper methods (unchanged from original)

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase alphanumeric tokens."""
        return re.findall(r"[a-z0-9]+", text.lower())

    def _compute_idf(self, docs_tokens: Iterable[List[str]]) -> Dict[str, float]:
        """Compute IDF scores for all tokens in the corpus."""
        docs_tokens_list = list(docs_tokens)
        doc_count = len(docs_tokens_list)
        df: Dict[str, int] = {}
        for tokens in docs_tokens_list:
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

    # Backward compatibility alias
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
