"""Postgres-backed TF-IDF memory store."""

from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, Iterable, List, Optional

import asyncpg


class MemoryStore:
    """Store and query project memory using Postgres persistence."""

    def __init__(self, db_pool: asyncpg.Pool, pattern_type_default: str = "document"):
        self.db_pool = db_pool
        self.pattern_type_default = pattern_type_default
        self.backend = "postgres_tfidf"
        self.last_error: Optional[str] = None

    async def upsert_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
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

    async def query_similar(
        self,
        query: str,
        top_k: int = 5,
        pattern_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content, metadata, pattern_type
                FROM memory_patterns
                """,
            )

        records = [dict(row) for row in rows]
        if not records:
            return []

        filtered_rows = [
            row
            for row in records
            if pattern_type is None or row.get("pattern_type") == pattern_type
        ]
        if not filtered_rows:
            return []

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

    async def count(self) -> int:
        async with self.db_pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(1) FROM memory_patterns")
        return int(count or 0)

    async def health(self) -> Dict[str, Any]:
        try:
            count = await self.count()
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "backend": self.backend,
                "count": 0,
                "last_error": self.last_error,
            }

        return {
            "backend": self.backend,
            "count": count,
            "last_error": self.last_error,
        }

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _compute_idf(self, docs_tokens: Iterable[List[str]]) -> Dict[str, float]:
        docs_tokens_list = list(docs_tokens)
        doc_count = len(docs_tokens_list)
        df: Dict[str, int] = {}
        for tokens in docs_tokens_list:
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1
        idf = {
            token: math.log((1 + doc_count) / (1 + freq)) + 1.0
            for token, freq in df.items()
        }
        return idf

    def _tfidf(self, tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
        if not tokens:
            return {}
        tf: Dict[str, float] = {}
        total = float(len(tokens))
        for token in tokens:
            tf[token] = tf.get(token, 0.0) + 1.0
        return {token: (count / total) * idf.get(token, 0.0) for token, count in tf.items()}

    def _cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        dot = sum(value * vec_b.get(token, 0.0) for token, value in vec_a.items())
        norm_a = math.sqrt(sum(value * value for value in vec_a.values()))
        norm_b = math.sqrt(sum(value * value for value in vec_b.values()))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)
