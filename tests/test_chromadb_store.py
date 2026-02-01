"""Tests for ChromaDB memory store backend."""

import pytest
import tempfile
import shutil

from src.memory import MemoryStoreBase, MemoryStoreRegistry

# Skip all tests if ChromaDB is not available
try:
    from src.memory import ChromaDBMemoryStore
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    ChromaDBMemoryStore = None

pytestmark = pytest.mark.skipif(
    not CHROMADB_AVAILABLE,
    reason="ChromaDB not installed"
)


@pytest.mark.asyncio
async def test_chromadb_implements_interface():
    """Test that ChromaDBMemoryStore implements the MemoryStoreBase interface."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    store = ChromaDBMemoryStore(collection_name="test_interface")
    
    assert isinstance(store, MemoryStoreBase)
    
    # Test all interface methods exist
    assert hasattr(store, 'store')
    assert hasattr(store, 'retrieve')
    assert hasattr(store, 'search')
    assert hasattr(store, 'update')
    assert hasattr(store, 'delete')
    assert hasattr(store, 'count')
    assert hasattr(store, 'health')
    assert hasattr(store, 'clear')


@pytest.mark.asyncio
async def test_chromadb_store_and_retrieve():
    """Test basic store and retrieve with ChromaDB."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    store = ChromaDBMemoryStore(collection_name="test_store_retrieve")
    
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
    
    # Cleanup
    await store.clear()


@pytest.mark.asyncio
async def test_chromadb_vector_search():
    """Test vector similarity search with ChromaDB."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    store = ChromaDBMemoryStore(collection_name="test_vector_search")
    
    # Store documents
    await store.store("doc1", "The quick brown fox jumps over the lazy dog")
    await store.store("doc2", "A fast auburn fox leaps above a sleepy canine")
    await store.store("doc3", "Python programming language is great for data science")
    
    # Search for similar to doc1 (should find doc2 as most similar)
    results = await store.search("quick fox jumping", top_k=2)
    assert len(results) >= 1
    assert results[0]["id"] in ["doc1", "doc2"]  # Should find semantically similar docs
    
    # Cleanup
    await store.clear()


@pytest.mark.asyncio
async def test_chromadb_search_with_filters():
    """Test search with metadata filters."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    store = ChromaDBMemoryStore(collection_name="test_search_filters")
    
    # Store documents with different types
    await store.store("doc1", "python code example", {"pattern_type": "code"})
    await store.store("doc2", "python snake facts", {"pattern_type": "animal"})
    await store.store("doc3", "javascript code example", {"pattern_type": "code"})
    
    # Search with filter
    results = await store.search("python", top_k=3, filters={"pattern_type": "code"})
    assert len(results) >= 1
    # Should only find code-related docs
    for result in results:
        assert result["metadata"].get("pattern_type") == "code"
    
    # Cleanup
    await store.clear()


@pytest.mark.asyncio
async def test_chromadb_update():
    """Test update functionality."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    store = ChromaDBMemoryStore(collection_name="test_update")
    
    # Store a document
    await store.store("doc1", "original text", {"version": 1})
    
    # Update text
    success = await store.update("doc1", text="updated text")
    assert success is True
    
    doc = await store.retrieve("doc1")
    assert doc["text"] == "updated text"
    assert doc["metadata"]["version"] == "1"  # ChromaDB converts to string
    
    # Update metadata
    success = await store.update("doc1", metadata={"version": 2, "author": "test"})
    assert success is True
    
    doc = await store.retrieve("doc1")
    assert doc["metadata"]["version"] == "2"
    assert doc["metadata"]["author"] == "test"
    
    # Update non-existent
    success = await store.update("missing", text="test")
    assert success is False
    
    # Cleanup
    await store.clear()


@pytest.mark.asyncio
async def test_chromadb_delete():
    """Test delete functionality."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    store = ChromaDBMemoryStore(collection_name="test_delete")
    
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
    
    # Cleanup
    await store.clear()


@pytest.mark.asyncio
async def test_chromadb_count():
    """Test count functionality."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    store = ChromaDBMemoryStore(collection_name="test_count")
    
    # Clear first
    await store.clear()
    
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
    
    # Cleanup
    await store.clear()


@pytest.mark.asyncio
async def test_chromadb_health():
    """Test health check."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    store = ChromaDBMemoryStore(collection_name="test_health")
    
    health = await store.health()
    assert health["backend"] == "chromadb"
    assert health["status"] == "healthy"
    assert "count" in health
    assert "collection" in health
    
    # Cleanup
    await store.clear()


@pytest.mark.asyncio
async def test_chromadb_clear():
    """Test clear functionality."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    store = ChromaDBMemoryStore(collection_name="test_clear")
    
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
async def test_chromadb_persistence():
    """Test persistence to disk."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create store with persistence
        store1 = ChromaDBMemoryStore(
            collection_name="test_persist",
            persist_directory=temp_dir
        )
        
        # Store a document
        await store1.store("doc1", "persistent data", {"key": "value"})
        
        # Create new store instance pointing to same directory
        store2 = ChromaDBMemoryStore(
            collection_name="test_persist",
            persist_directory=temp_dir
        )
        
        # Should be able to retrieve the document
        doc = await store2.retrieve("doc1")
        assert doc is not None
        assert doc["text"] == "persistent data"
        assert doc["metadata"]["key"] == "value"
        
        # Cleanup
        await store2.clear()
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_chromadb_backward_compatibility():
    """Test backward compatibility methods."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    store = ChromaDBMemoryStore(collection_name="test_backward_compat")
    
    # upsert_document
    doc_id = await store.upsert_document("doc1", "test", {"pattern_type": "prd"})
    assert doc_id == "doc1"
    
    # query_similar
    results = await store.query_similar("test", top_k=5, pattern_type="prd")
    assert len(results) >= 1
    assert results[0]["id"] == "doc1"
    
    # Cleanup
    await store.clear()


def test_chromadb_factory():
    """Test factory creation of ChromaDBMemoryStore."""
    if not CHROMADB_AVAILABLE:
        pytest.skip("ChromaDB not available")
    
    # Create using factory
    store = MemoryStoreRegistry.create("chromadb", collection_name="test_factory")
    
    assert isinstance(store, ChromaDBMemoryStore)
    assert isinstance(store, MemoryStoreBase)
    
    # Test alias
    store2 = MemoryStoreRegistry.create("chroma", collection_name="test_factory_alias")
    assert isinstance(store2, ChromaDBMemoryStore)


def test_chromadb_availability():
    """Test ChromaDB backend availability check."""
    is_available = MemoryStoreRegistry.is_available("chromadb")
    assert is_available == CHROMADB_AVAILABLE
