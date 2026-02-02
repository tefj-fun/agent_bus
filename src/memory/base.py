"""Abstract base class for memory storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MemoryStoreBase(ABC):
    """Abstract interface for memory storage backends.

    All memory store implementations must inherit from this class and implement
    the required methods. This allows for pluggable backends (Postgres, ChromaDB,
    in-memory, etc.) while maintaining a consistent API.

    Operations supported:
    - store: Save a document with metadata
    - retrieve: Get a document by ID
    - search: Find similar documents (semantic or keyword-based)
    - update: Modify an existing document
    - delete: Remove a document
    - count: Get total number of documents
    - health: Check backend health and get diagnostics
    """

    @abstractmethod
    async def store(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a document with optional metadata.

        Args:
            doc_id: Unique identifier for the document
            text: Document content
            metadata: Optional metadata dictionary

        Returns:
            The document ID (useful for auto-generated IDs)
        """
        pass

    @abstractmethod
    async def retrieve(
        self,
        doc_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID.

        Args:
            doc_id: Document identifier

        Returns:
            Dictionary with keys: id, text, metadata, or None if not found
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents.

        Args:
            query: Search query string
            top_k: Maximum number of results to return
            filters: Optional filters (e.g., {"pattern_type": "prd"})

        Returns:
            List of dicts with keys: id, text, metadata, score
            Sorted by relevance (highest score first)
        """
        pass

    @abstractmethod
    async def update(
        self,
        doc_id: str,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update an existing document.

        Args:
            doc_id: Document identifier
            text: New text content (if provided)
            metadata: New metadata (if provided, will merge with existing)

        Returns:
            True if update succeeded, False if document not found
        """
        pass

    @abstractmethod
    async def delete(
        self,
        doc_id: str,
    ) -> bool:
        """Delete a document.

        Args:
            doc_id: Document identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def count(
        self,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count documents matching optional filters.

        Args:
            filters: Optional filters (e.g., {"pattern_type": "prd"})

        Returns:
            Number of matching documents
        """
        pass

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Check backend health and return diagnostics.

        Returns:
            Dictionary with backend name, status, count, and any errors
            Example: {"backend": "postgres", "count": 42, "last_error": None}
        """
        pass

    @abstractmethod
    async def clear(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Clear documents matching optional filters.

        Useful for testing and maintenance.

        Args:
            filters: Optional filters (e.g., {"pattern_type": "test"})
                    If None, clears ALL documents (use with caution!)

        Returns:
            Number of documents deleted
        """
        pass
