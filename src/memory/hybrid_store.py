"""Hybrid memory store: Postgres for durability + ChromaDB for semantic search."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import asyncpg

from .base import MemoryStoreBase
from .postgres_store import PostgresMemoryStore
from .chroma_store import ChromaDBStore


class HybridMemoryStore(MemoryStoreBase):
    """Store documents in Postgres and index in ChromaDB for semantic search.

    - Writes go to Postgres first (durable).
    - ChromaDB is used for similarity search.
    - If ChromaDB is unavailable, search falls back to Postgres TF-IDF.
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        pattern_type_default: str = "document",
        collection_name: str = "agent_bus_patterns",
        persist_directory: str = "./data/chroma",
        host: Optional[str] = None,
        port: Optional[int] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        auto_embed: bool = True,
        **_kwargs,
    ):
        self.postgres = PostgresMemoryStore(
            db_pool=db_pool, pattern_type_default=pattern_type_default
        )
        self.chroma = ChromaDBStore(
            collection_name=collection_name,
            persist_directory=persist_directory,
            host=host,
            port=port,
            embedding_model=embedding_model,
            auto_embed=auto_embed,
        )
        self.backend = "hybrid"
        self.last_error: Optional[str] = None

    async def store(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        stored_id = await self.postgres.store(doc_id, text, metadata)
        try:
            await self.chroma.upsert_document(stored_id, text, metadata or {})
            self.last_error = None
        except Exception as exc:
            # Keep durable copy in Postgres even if vector index fails
            self.last_error = str(exc)
        return stored_id

    async def retrieve(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return await self.postgres.retrieve(doc_id)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            pattern_type = filters.get("pattern_type") if filters else None
            results = await self.chroma.query_similar(
                query=query, top_k=top_k, pattern_type=pattern_type
            )
            if results:
                self.last_error = None
                return results
        except Exception as exc:
            self.last_error = str(exc)

        # Fallback to TF-IDF search in Postgres
        return await self.postgres.search(query=query, top_k=top_k, filters=filters)

    async def update(
        self,
        doc_id: str,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        updated = await self.postgres.update(doc_id, text=text, metadata=metadata)
        if not updated:
            return False
        try:
            current = await self.postgres.retrieve(doc_id)
            if current:
                await self.chroma.upsert_document(
                    doc_id, current.get("text", ""), current.get("metadata", {})
                )
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)
        return True

    async def delete(self, doc_id: str) -> bool:
        deleted = await self.postgres.delete(doc_id)
        try:
            await self.chroma.delete_document(doc_id)
        except Exception:
            pass
        return deleted

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        return await self.postgres.count(filters)

    async def health(self) -> Dict[str, Any]:
        pg = await self.postgres.health()
        ch = await self.chroma.health()
        count = pg.get("count", 0)
        status = "healthy" if pg.get("status") == "healthy" else "error"
        return {
            "backend": self.backend,
            "status": status,
            "count": count,
            "postgres": pg,
            "chroma": ch,
            "last_error": self.last_error,
        }

    async def clear(self, filters: Optional[Dict[str, Any]] = None) -> int:
        deleted = await self.postgres.clear(filters)
        try:
            if filters and filters.get("pattern_type"):
                self.chroma.collection.delete(where={"pattern_type": filters.get("pattern_type")})
            else:
                self.chroma.collection.delete(where={})
        except Exception:
            pass
        return deleted

    async def sync_from_postgres(self) -> int:
        """Backfill ChromaDB from Postgres memory_patterns."""
        return await self.chroma.migrate_from_postgres(self.postgres)
