"""Factory and registry for memory store backends."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Type

from .base import MemoryStoreBase
from .postgres_store import PostgresMemoryStore
from .memory_store import InMemoryStore

logger = logging.getLogger(__name__)


# Lazy import for ChromaDB (optional dependency)
def _get_chroma_store() -> Type[MemoryStoreBase]:
    """Lazy import ChromaDB store to avoid import errors if not installed."""
    try:
        from .chroma_store import ChromaDBMemoryStore

        return ChromaDBMemoryStore
    except ImportError:
        raise ImportError(
            "ChromaDB backend requires chromadb to be installed. "
            "Install it with: pip install chromadb"
        )


def _get_hybrid_store() -> Type[MemoryStoreBase]:
    """Lazy import hybrid store to avoid import errors if chromadb isn't installed."""
    try:
        from .hybrid_store import HybridMemoryStore

        return HybridMemoryStore
    except ImportError as exc:
        raise ImportError(
            "Hybrid backend requires chromadb to be installed. "
            "Install it with: pip install chromadb"
        ) from exc


class MemoryStoreRegistry:
    """Registry for memory store backend implementations.

    Allows registration and creation of different memory store backends.
    Supports built-in backends (postgres, chromadb, in-memory) and custom
    backends can be registered at runtime.

    Example:
        # Get default backend (postgres)
        store = MemoryStoreRegistry.create("postgres", db_pool=pool)

        # Use in-memory for testing
        store = MemoryStoreRegistry.create("in-memory")

        # Register custom backend
        MemoryStoreRegistry.register("custom", CustomStore)
        store = MemoryStoreRegistry.create("custom", **custom_config)
    """

    _backends: Dict[str, Type[MemoryStoreBase]] = {
        "postgres": PostgresMemoryStore,
        "in-memory": InMemoryStore,
        "memory": InMemoryStore,  # Alias
    }

    _lazy_backends: Dict[str, Callable[[], Type[MemoryStoreBase]]] = {
        "chromadb": _get_chroma_store,
        "chroma": _get_chroma_store,  # Alias
        "hybrid": _get_hybrid_store,
    }

    @classmethod
    def register(cls, name: str, backend_class: Type[MemoryStoreBase]) -> None:
        """Register a custom memory store backend.

        Args:
            name: Backend name (e.g., "redis", "elasticsearch")
            backend_class: Backend class inheriting from MemoryStoreBase
        """
        if not issubclass(backend_class, MemoryStoreBase):
            raise TypeError(f"Backend class must inherit from MemoryStoreBase, got {backend_class}")

        cls._backends[name] = backend_class
        logger.info(f"Registered memory store backend: {name}")

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a memory store backend.

        Args:
            name: Backend name to unregister
        """
        if name in cls._backends:
            del cls._backends[name]
            logger.info(f"Unregistered memory store backend: {name}")

    @classmethod
    def create(
        cls,
        backend: str = "postgres",
        **kwargs: Any,
    ) -> MemoryStoreBase:
        """Create a memory store instance.

        Args:
            backend: Backend type ("postgres", "chromadb", "in-memory")
            **kwargs: Backend-specific configuration

        Returns:
            Initialized memory store instance

        Raises:
            ValueError: If backend is not registered

        Example:
            # Postgres backend
            store = MemoryStoreRegistry.create("postgres", db_pool=pool)

            # ChromaDB backend
            store = MemoryStoreRegistry.create(
                "chromadb",
                collection_name="my_memory",
                persist_directory="/data/chroma"
            )

            # In-memory backend (no args needed)
            store = MemoryStoreRegistry.create("in-memory")
        """
        # Check lazy backends first
        if backend in cls._lazy_backends:
            try:
                backend_class = cls._lazy_backends[backend]()
            except ImportError as exc:
                raise ValueError(f"Backend '{backend}' is not available: {exc}") from exc
        elif backend in cls._backends:
            backend_class = cls._backends[backend]
        else:
            available = list(cls._backends.keys()) + list(cls._lazy_backends.keys())
            raise ValueError(
                f"Unknown backend: {backend}. Available backends: {', '.join(available)}"
            )

        logger.info(f"Creating memory store backend: {backend}")
        return backend_class(**kwargs)

    @classmethod
    def list_backends(cls) -> list[str]:
        """List all available backend names.

        Returns:
            List of registered backend names
        """
        return sorted(list(cls._backends.keys()) + list(cls._lazy_backends.keys()))

    @classmethod
    def is_available(cls, backend: str) -> bool:
        """Check if a backend is available.

        Args:
            backend: Backend name to check

        Returns:
            True if backend is registered and available
        """
        if backend in cls._backends:
            return True

        if backend in cls._lazy_backends:
            try:
                cls._lazy_backends[backend]()
                return True
            except ImportError:
                return False

        return False


# Convenience function for backward compatibility
def create_memory_store(
    backend: str = "postgres",
    **kwargs: Any,
) -> MemoryStoreBase:
    """Create a memory store instance (convenience function).

    This is a shorthand for MemoryStoreRegistry.create().

    Args:
        backend: Backend type ("postgres", "chromadb", "in-memory")
        **kwargs: Backend-specific configuration

    Returns:
        Initialized memory store instance
    """
    return MemoryStoreRegistry.create(backend, **kwargs)
