"""ChromaDB-backed vector memory store with sentence-transformer embeddings."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from .embedding_generator import EmbeddingGenerator


class ChromaDBStore:
    """Vector memory store using ChromaDB for semantic similarity search."""

    def __init__(
        self,
        collection_name: str = "agent_bus_memory",
        persist_directory: str = "./chroma_data",
        host: Optional[str] = None,
        port: Optional[int] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        auto_embed: bool = True,
    ):
        """
        Initialize ChromaDB store.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory for local persistence (ignored if host/port provided)
            host: ChromaDB server host (for client mode)
            port: ChromaDB server port (for client mode)
            embedding_model: Sentence-transformer model name
            auto_embed: Automatically generate embeddings if not provided
        """
        self.collection_name = collection_name
        self.backend = "chromadb"
        self.last_error: Optional[str] = None
        self.auto_embed = auto_embed

        # Initialize embedding generator
        if auto_embed:
            self.embedding_generator = EmbeddingGenerator(model_name=embedding_model)
        else:
            self.embedding_generator = None

        # Initialize client (local or remote)
        if host and port:
            self.client = chromadb.HttpClient(host=host, port=port)
            self.mode = "client"
        else:
            self.client = chromadb.Client(
                Settings(
                    persist_directory=persist_directory,
                    anonymized_telemetry=False,
                )
            )
            self.mode = "local"

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},  # Use cosine similarity
        )

    async def upsert_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """
        Store or update a document in the vector database.

        Args:
            doc_id: Unique document identifier
            text: Document content
            metadata: Optional metadata dict
            embedding: Pre-computed embedding (if None, will auto-generate if enabled)

        Returns:
            Document ID
        """
        try:
            # Prepare metadata (ChromaDB requires string values)
            meta = metadata or {}
            meta_str = {k: str(v) for k, v in meta.items()}

            # Generate embedding if needed
            if embedding is None and self.auto_embed and self.embedding_generator:
                # For long documents, use chunking
                if len(text) > 500:
                    embedding, chunks = self.embedding_generator.generate_chunked(text)
                    meta_str["chunks"] = str(len(chunks))
                else:
                    embedding = self.embedding_generator.generate(text)

            # Upsert document
            if embedding:
                self.collection.upsert(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[meta_str],
                    embeddings=[embedding],
                )
            else:
                # Let ChromaDB auto-generate embeddings
                self.collection.upsert(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[meta_str],
                )

            self.last_error = None
            return doc_id

        except Exception as exc:
            self.last_error = str(exc)
            raise

    async def query_similar(
        self,
        query: str,
        top_k: int = 5,
        pattern_type: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query for similar documents using vector similarity.

        Args:
            query: Query text
            top_k: Number of results to return
            pattern_type: Optional filter by pattern_type metadata
            query_embedding: Pre-computed query embedding (if None, will auto-generate if enabled)

        Returns:
            List of results with id, text, metadata, and score (distance)
        """
        try:
            # Build where filter if pattern_type specified
            where = None
            if pattern_type:
                where = {"pattern_type": pattern_type}

            # Generate query embedding if needed
            if query_embedding is None and self.auto_embed and self.embedding_generator:
                query_embedding = self.embedding_generator.generate(query)

            # Query collection
            if query_embedding:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=where,
                )
            else:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where=where,
                )

            # Format results
            formatted = []
            if results and results.get("ids"):
                for i, doc_id in enumerate(results["ids"][0]):
                    formatted.append(
                        {
                            "id": doc_id,
                            "text": results["documents"][0][i] if results.get("documents") else "",
                            "metadata": (
                                results["metadatas"][0][i] if results.get("metadatas") else {}
                            ),
                            "score": (
                                1.0 - results["distances"][0][i]
                                if results.get("distances")
                                else 0.0
                            ),  # Convert distance to similarity
                        }
                    )

            self.last_error = None
            return formatted

        except Exception as exc:
            self.last_error = str(exc)
            raise

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by ID.

        Args:
            doc_id: Document identifier

        Returns:
            Document dict or None if not found
        """
        try:
            result = self.collection.get(ids=[doc_id])
            if result and result.get("ids"):
                return {
                    "id": result["ids"][0],
                    "text": result["documents"][0] if result.get("documents") else "",
                    "metadata": result["metadatas"][0] if result.get("metadatas") else {},
                }
            return None
        except Exception:
            return None

    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document by ID.

        Args:
            doc_id: Document identifier

        Returns:
            True if deleted, False otherwise
        """
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception:
            return False

    async def count(self) -> int:
        """Get total count of documents in collection."""
        try:
            return self.collection.count()
        except Exception:
            return 0

    async def health(self) -> Dict[str, Any]:
        """
        Check health of ChromaDB connection.

        Returns:
            Health status dict
        """
        try:
            count = await self.count()
            embedding_info = {}
            if self.embedding_generator:
                embedding_info = self.embedding_generator.get_info()

            return {
                "backend": self.backend,
                "mode": self.mode,
                "collection": self.collection_name,
                "count": count,
                "auto_embed": self.auto_embed,
                "embedding_info": embedding_info,
                "last_error": self.last_error,
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "backend": self.backend,
                "mode": self.mode,
                "collection": self.collection_name,
                "count": 0,
                "last_error": self.last_error,
            }

    async def migrate_from_postgres(self, postgres_store) -> int:
        """
        Migrate documents from existing Postgres TF-IDF store.

        Args:
            postgres_store: MemoryStore instance (Postgres-based)

        Returns:
            Number of documents migrated
        """
        try:
            # Get all patterns from Postgres

            async with postgres_store.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, content, metadata, pattern_type
                    FROM memory_patterns
                    ORDER BY created_at
                    """)

            # Upsert to ChromaDB
            migrated = 0
            for row in rows:
                doc_id = row["id"]
                text = row["content"]
                metadata = row.get("metadata") or {}
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)

                # Add pattern_type to metadata
                metadata["pattern_type"] = row.get("pattern_type", "document")

                await self.upsert_document(doc_id, text, metadata)
                migrated += 1

            return migrated

        except Exception as exc:
            self.last_error = str(exc)
            raise
