"""Backward compatibility shim for old MemoryStore import.

This module maintains backward compatibility for code that imports:
    from src.memory.store import MemoryStore

The MemoryStore class has been renamed to PostgresMemoryStore and moved
to postgres_store.py. This shim ensures existing code continues to work.
"""

from .postgres_store import PostgresMemoryStore

# Backward compatibility: MemoryStore = PostgresMemoryStore
MemoryStore = PostgresMemoryStore

__all__ = ["MemoryStore"]
