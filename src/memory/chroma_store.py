"""ChromaDB-backed memory store for vector similarity search."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

from .base import MemoryStoreBase


logger = logging.getLogger(__name__)


class ChromaDBMemoryStore(MemoryStoreBase):
    """Store and query project memory using ChromaDB for vector similarity search.
    
    This backend uses ChromaDB's built-in embedding models to store and search
    documents based on semantic similarity. Ideal for pattern recognition and
    semantic search across memory patterns.
    
    Requires chromadb to be installed:
        pip install chromadb
    """

    def __init__(
        self,
        collection_name: str = "agent_bus_memory",
        persist_directory: Optional[str] = None,
        embedding_function: Optional[Any] = None,
    ):
        """Initialize ChromaDB memory store.
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist data (None for in-memory)
            embedding_function: Custom embedding function (None for default)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "chromadb is not installed. Install it with: pip install chromadb"
            )
        
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.backend = "chromadb"
        self.last_error: Optional[str] = None
        
        # Initialize ChromaDB client
        if persist_directory:
            self._client = chromadb.PersistentClient(path=persist_directory)
        else:
            self._client = chromadb.Client()
        
        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function,
        )
        
        logger.info(f"Initialized ChromaDB store: collection={collection_name}")

    async def store(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a document in ChromaDB."""
        try:
            # ChromaDB metadata values must be strings, ints, floats, or bools
            # Convert complex metadata to JSON strings
            clean_metadata = self._sanitize_metadata(metadata or {})
            
            # Upsert to collection (will update if exists)
            self._collection.upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[clean_metadata],
            )
            
            return doc_id
        except Exception as exc:
            self.last_error = str(exc)
            logger.error(f"Failed to store document {doc_id}: {exc}")
            raise

    async def retrieve(
        self,
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        try:
            result = self._collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"],
            )
            
            if not result["ids"]:
                return None
            
            return {
                "id": result["ids"][0],
                "text": result["documents"][0],
                "metadata": result["metadatas"][0] or {},
            }
        except Exception as exc:
            self.last_error = str(exc)
            logger.error(f"Failed to retrieve document {doc_id}: {exc}")
            return None

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity.
        
        Filters support ChromaDB's where clause syntax:
        - {"pattern_type": "prd"} - exact match
        - {"pattern_type": {"$in": ["prd", "plan"]}} - multiple values
        """
        try:
            # Prepare where clause from filters
            where = None
            if filters:
                where = self._build_where_clause(filters)
            
            # Query collection
            results = self._collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
            
            # Format results
            documents = []
            if results["ids"]:
                for i in range(len(results["ids"][0])):
                    # ChromaDB returns distances (lower is better)
                    # Convert to similarity score (higher is better)
                    distance = results["distances"][0][i]
                    score = 1.0 / (1.0 + distance)  # Convert distance to similarity
                    
                    documents.append({
                        "id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] or {},
                        "score": score,
                    })
            
            return documents
        except Exception as exc:
            self.last_error = str(exc)
            logger.error(f"Failed to search documents: {exc}")
            return []

    async def update(
        self,
        doc_id: str,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update an existing document."""
        try:
            # Check if document exists
            existing = await self.retrieve(doc_id)
            if not existing:
                return False
            
            # Prepare updates
            new_text = text if text is not None else existing["text"]
            
            if metadata is None:
                new_metadata = existing["metadata"]
            else:
                # Merge metadata
                new_metadata = {**existing["metadata"], **metadata}
            
            # Update in ChromaDB (upsert)
            clean_metadata = self._sanitize_metadata(new_metadata)
            self._collection.upsert(
                ids=[doc_id],
                documents=[new_text],
                metadatas=[clean_metadata],
            )
            
            return True
        except Exception as exc:
            self.last_error = str(exc)
            logger.error(f"Failed to update document {doc_id}: {exc}")
            return False

    async def delete(
        self,
        doc_id: str,
    ) -> bool:
        """Delete a document by ID."""
        try:
            # Check if exists first
            existing = await self.retrieve(doc_id)
            if not existing:
                return False
            
            self._collection.delete(ids=[doc_id])
            return True
        except Exception as exc:
            self.last_error = str(exc)
            logger.error(f"Failed to delete document {doc_id}: {exc}")
            return False

    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count documents matching optional filters."""
        try:
            where = None
            if filters:
                where = self._build_where_clause(filters)
            
            # Get all matching documents
            result = self._collection.get(
                where=where,
                include=[],  # Don't need documents, just count
            )
            
            return len(result["ids"])
        except Exception as exc:
            self.last_error = str(exc)
            logger.error(f"Failed to count documents: {exc}")
            return 0

    async def health(self) -> Dict[str, Any]:
        """Check backend health and return diagnostics."""
        try:
            count = await self.count()
            return {
                "backend": self.backend,
                "status": "healthy",
                "collection": self.collection_name,
                "count": count,
                "last_error": self.last_error,
            }
        except Exception as exc:
            self.last_error = str(exc)
            return {
                "backend": self.backend,
                "status": "error",
                "collection": self.collection_name,
                "count": 0,
                "last_error": str(exc),
            }

    async def clear(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Clear documents matching optional filters."""
        try:
            where = None
            if filters:
                where = self._build_where_clause(filters)
            
            # Get IDs to delete
            result = self._collection.get(
                where=where,
                include=[],
            )
            
            if result["ids"]:
                self._collection.delete(ids=result["ids"])
            
            return len(result["ids"])
        except Exception as exc:
            self.last_error = str(exc)
            logger.error(f"Failed to clear documents: {exc}")
            return 0

    # Helper methods

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize metadata for ChromaDB (only str, int, float, bool allowed)."""
        clean = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                clean[key] = value
            elif value is None:
                continue  # Skip None values
            else:
                # Convert complex types to strings
                clean[key] = str(value)
        return clean

    def _build_where_clause(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build ChromaDB where clause from simple filters.
        
        Converts simple filters like {"pattern_type": "prd"} to ChromaDB format.
        For more complex queries, users can pass ChromaDB where syntax directly.
        """
        # If filters already look like a ChromaDB where clause, use as-is
        if any(key.startswith("$") for key in filters.keys()):
            return filters
        
        # Convert simple key-value filters to ChromaDB format
        return filters

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
