"""Memory subsystem for agent_bus.

This module provides a unified interface for memory storage with multiple backend
support including Postgres (TF-IDF), ChromaDB (vector embeddings), and in-memory
storage for testing.

Quick start:
    # Using factory
    from memory import create_memory_store
    store = create_memory_store("postgres", db_pool=pool)
    
    # Direct instantiation
    from memory import PostgresMemoryStore
    store = PostgresMemoryStore(db_pool=pool)
    
    # Backend registry
    from memory import MemoryStoreRegistry
    MemoryStoreRegistry.list_backends()  # ['postgres', 'chromadb', 'in-memory']
"""

from .base import MemoryStoreBase
from .postgres_store import PostgresMemoryStore
from .memory_store import InMemoryStore
from .factory import MemoryStoreRegistry, create_memory_store
from .hybrid_store import HybridMemoryStore

# Lazy import for ChromaDB (optional dependency)
try:
    from .chroma_store import ChromaDBMemoryStore

    _CHROMADB_AVAILABLE = True
except ImportError:
    ChromaDBMemoryStore = None
    _CHROMADB_AVAILABLE = False

# Backward compatibility: MemoryStore = PostgresMemoryStore
MemoryStore = PostgresMemoryStore

__all__ = [
    # Base interface
    "MemoryStoreBase",
    # Backends
    "PostgresMemoryStore",
    "InMemoryStore",
    "ChromaDBMemoryStore",  # May be None if chromadb not installed
    "HybridMemoryStore",
    # Factory
    "MemoryStoreRegistry",
    "create_memory_store",
    # Backward compatibility
    "MemoryStore",
]
