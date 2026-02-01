"""Tests for the unified MemoryStore interface and all backends."""

import json
import pytest

from src.memory import (
    MemoryStoreBase,
    PostgresMemoryStore,
    InMemoryStore,
    MemoryStoreRegistry,
    create_memory_store,
)


class FakePool:
    """Fake asyncpg pool for testing."""

    def __init__(self):
        self.memory_rows = []

    class _Conn:
        def __init__(self, pool):
            self._pool = pool

        async def execute(self, query, *args):
            # Handle INSERT/UPDATE
            if "INSERT INTO memory_patterns" in query or "UPDATE memory_patterns" in query:
                if len(args) >= 4:
                    doc_id, pattern_type, content, metadata = args[:4]
                    if isinstance(metadata, str):
                        s = metadata.strip()
                        if s.startswith("{") or s.startswith("["):
                            metadata = json.loads(metadata)
                        else:
                            metadata = {"raw": metadata}

                    existing = next(
                        (row for row in self._pool.memory_rows if row["id"] == doc_id),
                        None,
                    )
                    record = {
                        "id": doc_id,
                        "pattern_type": pattern_type,
                        "content": content,
                        "metadata": metadata,
                    }
                    if existing:
                        existing.update(record)
                    else:
                        self._pool.memory_rows.append(record)
                return "INSERT 0 1"

            # Handle DELETE
            elif "DELETE FROM memory_patterns" in query:
                if args:
                    # Delete by ID
                    doc_id = args[0]
                    before = len(self._pool.memory_rows)
                    self._pool.memory_rows = [
                        row for row in self._pool.memory_rows if row["id"] != doc_id
                    ]
                    after = len(self._pool.memory_rows)
                    deleted = before - after
                else:
                    # Delete all
                    deleted = len(self._pool.memory_rows)
                    self._pool.memory_rows.clear()
                return f"DELETE {deleted}"

            return None

        async def fetch(self, *_args, **_kwargs):
            return list(self._pool.memory_rows)

        async def fetchrow(self, query, *args):
            if args:
                doc_id = args[0]
                for row in self._pool.memory_rows:
                    if row["id"] == doc_id:
                        return row
            return None

        async def fetchval(self, query, *args):
            if "WHERE pattern_type" in query and args:
                pattern_type = args[0]
                count = sum(
                    1 for row in self._pool.memory_rows if row.get("pattern_type") == pattern_type
                )
                return count
            return len(self._pool.memory_rows)

    class _Acquire:
        def __init__(self, pool):
            self._pool = pool

        async def __aenter__(self):
            return FakePool._Conn(self._pool)

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def acquire(self):
        return FakePool._Acquire(self)


@pytest.mark.asyncio
async def test_postgres_store_implements_interface():
    """Test that PostgresMemoryStore implements the MemoryStoreBase interface."""
    pool = FakePool()
    store = PostgresMemoryStore(db_pool=pool)

    assert isinstance(store, MemoryStoreBase)

    # Test all interface methods exist
    assert hasattr(store, "store")
    assert hasattr(store, "retrieve")
    assert hasattr(store, "search")
    assert hasattr(store, "update")
    assert hasattr(store, "delete")
    assert hasattr(store, "count")
    assert hasattr(store, "health")
    assert hasattr(store, "clear")


@pytest.mark.asyncio
async def test_inmemory_store_implements_interface():
    """Test that InMemoryStore implements the MemoryStoreBase interface."""
    store = InMemoryStore()

    assert isinstance(store, MemoryStoreBase)

    # Test all interface methods exist
    assert hasattr(store, "store")
    assert hasattr(store, "retrieve")
    assert hasattr(store, "search")
    assert hasattr(store, "update")
    assert hasattr(store, "delete")
    assert hasattr(store, "count")
    assert hasattr(store, "health")
    assert hasattr(store, "clear")


@pytest.mark.asyncio
async def test_store_and_retrieve_postgres():
    """Test basic store and retrieve operations with PostgresMemoryStore."""
    pool = FakePool()
    store = PostgresMemoryStore(db_pool=pool)

    # Store a document
    doc_id = await store.store("doc1", "Hello world", {"type": "greeting"})
    assert doc_id == "doc1"

    # Retrieve it
    doc = await store.retrieve("doc1")
    assert doc is not None
    assert doc["id"] == "doc1"
    assert doc["text"] == "Hello world"
    assert doc["metadata"]["type"] == "greeting"

    # Retrieve non-existent
    missing = await store.retrieve("missing")
    assert missing is None


@pytest.mark.asyncio
async def test_store_and_retrieve_inmemory():
    """Test basic store and retrieve operations with InMemoryStore."""
    store = InMemoryStore()

    # Store a document
    doc_id = await store.store("doc1", "Hello world", {"type": "greeting"})
    assert doc_id == "doc1"

    # Retrieve it
    doc = await store.retrieve("doc1")
    assert doc is not None
    assert doc["id"] == "doc1"
    assert doc["text"] == "Hello world"
    assert doc["metadata"]["type"] == "greeting"

    # Retrieve non-existent
    missing = await store.retrieve("missing")
    assert missing is None


@pytest.mark.asyncio
async def test_search_postgres():
    """Test search functionality with PostgresMemoryStore."""
    pool = FakePool()
    store = PostgresMemoryStore(db_pool=pool)

    # Store documents
    await store.store("doc1", "python programming", {"pattern_type": "code"})
    await store.store("doc2", "python snake", {"pattern_type": "animal"})
    await store.store("doc3", "javascript programming", {"pattern_type": "code"})

    # Search all
    results = await store.search("python", top_k=3)
    assert len(results) == 2  # doc1 and doc2 have "python"

    # Search with filter
    results = await store.search("python", top_k=3, filters={"pattern_type": "code"})
    assert len(results) == 1
    assert results[0]["id"] == "doc1"


@pytest.mark.asyncio
async def test_search_inmemory():
    """Test search functionality with InMemoryStore."""
    store = InMemoryStore()

    # Store documents
    await store.store("doc1", "python programming", {"pattern_type": "code"})
    await store.store("doc2", "python snake", {"pattern_type": "animal"})
    await store.store("doc3", "javascript programming", {"pattern_type": "code"})

    # Search all
    results = await store.search("python", top_k=3)
    assert len(results) == 2  # doc1 and doc2 have "python"

    # Search with filter
    results = await store.search("python", top_k=3, filters={"pattern_type": "code"})
    assert len(results) == 1
    assert results[0]["id"] == "doc1"


@pytest.mark.asyncio
async def test_update_postgres():
    """Test update functionality with PostgresMemoryStore."""
    pool = FakePool()
    store = PostgresMemoryStore(db_pool=pool)

    # Store a document
    await store.store("doc1", "original text", {"version": 1})

    # Update text
    success = await store.update("doc1", text="updated text")
    assert success is True

    doc = await store.retrieve("doc1")
    assert doc["text"] == "updated text"
    assert doc["metadata"]["version"] == 1

    # Update metadata
    success = await store.update("doc1", metadata={"version": 2})
    assert success is True

    doc = await store.retrieve("doc1")
    assert doc["metadata"]["version"] == 2

    # Update non-existent
    success = await store.update("missing", text="test")
    assert success is False


@pytest.mark.asyncio
async def test_update_inmemory():
    """Test update functionality with InMemoryStore."""
    store = InMemoryStore()

    # Store a document
    await store.store("doc1", "original text", {"version": 1})

    # Update text
    success = await store.update("doc1", text="updated text")
    assert success is True

    doc = await store.retrieve("doc1")
    assert doc["text"] == "updated text"
    assert doc["metadata"]["version"] == 1

    # Update metadata
    success = await store.update("doc1", metadata={"version": 2})
    assert success is True

    doc = await store.retrieve("doc1")
    assert doc["metadata"]["version"] == 2

    # Update non-existent
    success = await store.update("missing", text="test")
    assert success is False


@pytest.mark.asyncio
async def test_delete_postgres():
    """Test delete functionality with PostgresMemoryStore."""
    pool = FakePool()
    store = PostgresMemoryStore(db_pool=pool)

    # Store and delete
    await store.store("doc1", "test")
    success = await store.delete("doc1")
    assert success is True

    # Verify deleted
    doc = await store.retrieve("doc1")
    assert doc is None

    # Delete non-existent
    success = await store.delete("missing")
    assert success is False


@pytest.mark.asyncio
async def test_delete_inmemory():
    """Test delete functionality with InMemoryStore."""
    store = InMemoryStore()

    # Store and delete
    await store.store("doc1", "test")
    success = await store.delete("doc1")
    assert success is True

    # Verify deleted
    doc = await store.retrieve("doc1")
    assert doc is None

    # Delete non-existent
    success = await store.delete("missing")
    assert success is False


@pytest.mark.asyncio
async def test_count_postgres():
    """Test count functionality with PostgresMemoryStore."""
    pool = FakePool()
    store = PostgresMemoryStore(db_pool=pool)

    # Empty
    count = await store.count()
    assert count == 0

    # Store documents
    await store.store("doc1", "test1", {"pattern_type": "type_a"})
    await store.store("doc2", "test2", {"pattern_type": "type_a"})
    await store.store("doc3", "test3", {"pattern_type": "type_b"})

    # Count all
    count = await store.count()
    assert count == 3

    # Count with filter
    count = await store.count(filters={"pattern_type": "type_a"})
    assert count == 2


@pytest.mark.asyncio
async def test_count_inmemory():
    """Test count functionality with InMemoryStore."""
    store = InMemoryStore()

    # Empty
    count = await store.count()
    assert count == 0

    # Store documents
    await store.store("doc1", "test1", {"pattern_type": "type_a"})
    await store.store("doc2", "test2", {"pattern_type": "type_a"})
    await store.store("doc3", "test3", {"pattern_type": "type_b"})

    # Count all
    count = await store.count()
    assert count == 3

    # Count with filter
    count = await store.count(filters={"pattern_type": "type_a"})
    assert count == 2


@pytest.mark.asyncio
async def test_health_postgres():
    """Test health check with PostgresMemoryStore."""
    pool = FakePool()
    store = PostgresMemoryStore(db_pool=pool)

    health = await store.health()
    assert health["backend"] == "postgres_tfidf"
    assert health["status"] == "healthy"
    assert health["count"] == 0
    assert health["last_error"] is None


@pytest.mark.asyncio
async def test_health_inmemory():
    """Test health check with InMemoryStore."""
    store = InMemoryStore()

    health = await store.health()
    assert health["backend"] == "in_memory"
    assert health["status"] == "healthy"
    assert health["count"] == 0
    assert health["last_error"] is None


@pytest.mark.asyncio
async def test_clear_postgres():
    """Test clear functionality with PostgresMemoryStore."""
    pool = FakePool()
    store = PostgresMemoryStore(db_pool=pool)

    # Store documents
    await store.store("doc1", "test1", {"pattern_type": "type_a"})
    await store.store("doc2", "test2", {"pattern_type": "type_a"})
    await store.store("doc3", "test3", {"pattern_type": "type_b"})

    # Clear with filter
    deleted = await store.clear(filters={"pattern_type": "type_a"})
    assert deleted == 2

    count = await store.count()
    assert count == 1

    # Clear all
    deleted = await store.clear()
    assert deleted == 1

    count = await store.count()
    assert count == 0


@pytest.mark.asyncio
async def test_clear_inmemory():
    """Test clear functionality with InMemoryStore."""
    store = InMemoryStore()

    # Store documents
    await store.store("doc1", "test1", {"pattern_type": "type_a"})
    await store.store("doc2", "test2", {"pattern_type": "type_a"})
    await store.store("doc3", "test3", {"pattern_type": "type_b"})

    # Clear with filter
    deleted = await store.clear(filters={"pattern_type": "type_a"})
    assert deleted == 2

    count = await store.count()
    assert count == 1

    # Clear all
    deleted = await store.clear()
    assert deleted == 1

    count = await store.count()
    assert count == 0


@pytest.mark.asyncio
async def test_backward_compatibility_postgres():
    """Test backward compatibility methods with PostgresMemoryStore."""
    pool = FakePool()
    store = PostgresMemoryStore(db_pool=pool)

    # upsert_document
    doc_id = await store.upsert_document("doc1", "test", {"pattern_type": "prd"})
    assert doc_id == "doc1"

    # query_similar
    results = await store.query_similar("test", top_k=5, pattern_type="prd")
    assert len(results) == 1
    assert results[0]["id"] == "doc1"


@pytest.mark.asyncio
async def test_factory_create_postgres():
    """Test factory creation of PostgresMemoryStore."""
    pool = FakePool()
    store = create_memory_store("postgres", db_pool=pool)

    assert isinstance(store, PostgresMemoryStore)
    assert isinstance(store, MemoryStoreBase)


@pytest.mark.asyncio
async def test_factory_create_inmemory():
    """Test factory creation of InMemoryStore."""
    store = create_memory_store("in-memory")

    assert isinstance(store, InMemoryStore)
    assert isinstance(store, MemoryStoreBase)

    # Test alias
    store2 = create_memory_store("memory")
    assert isinstance(store2, InMemoryStore)


def test_registry_list_backends():
    """Test listing available backends."""
    backends = MemoryStoreRegistry.list_backends()

    assert "postgres" in backends
    assert "in-memory" in backends
    assert "memory" in backends
    assert "chromadb" in backends or "chroma" in backends


def test_registry_is_available():
    """Test checking backend availability."""
    assert MemoryStoreRegistry.is_available("postgres") is True
    assert MemoryStoreRegistry.is_available("in-memory") is True
    assert MemoryStoreRegistry.is_available("nonexistent") is False


def test_factory_unknown_backend():
    """Test factory with unknown backend."""
    with pytest.raises(ValueError, match="Unknown backend"):
        create_memory_store("nonexistent")
