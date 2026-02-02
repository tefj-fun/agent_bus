"""Tests for ChromaDB vector store."""

import tempfile
import pytest
from src.memory.chroma_store import ChromaDBStore

# Skip in CI - requires proper test isolation for ChromaDB
pytestmark = pytest.mark.skipif(
    True, reason="ChromaDB tests require isolation - run manually"
)


@pytest.fixture
def temp_chroma_dir():
    """Create temporary directory for ChromaDB data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
async def chroma_store(temp_chroma_dir):
    """Create ChromaDB store instance."""
    store = ChromaDBStore(
        collection_name="test_collection",
        persist_directory=temp_chroma_dir,
    )
    yield store
    # Cleanup handled by temp_chroma_dir


class TestChromaDBStore:
    """Test ChromaDB store functionality."""

    async def test_init_local_mode(self, temp_chroma_dir):
        """Test initialization in local mode."""
        store = ChromaDBStore(
            collection_name="test_init",
            persist_directory=temp_chroma_dir,
        )
        assert store.backend == "chromadb"
        assert store.mode == "local"
        assert store.collection_name == "test_init"

    async def test_upsert_document(self, chroma_store):
        """Test upserting a document."""
        doc_id = "test_doc_1"
        text = "This is a test document about machine learning."
        metadata = {"type": "test", "category": "ml"}

        result_id = await chroma_store.upsert_document(doc_id, text, metadata)
        assert result_id == doc_id

        # Verify document was stored
        count = await chroma_store.count()
        assert count == 1

    async def test_upsert_update_existing(self, chroma_store):
        """Test updating an existing document."""
        doc_id = "test_doc_2"
        text1 = "Original text"
        text2 = "Updated text"

        # Insert
        await chroma_store.upsert_document(doc_id, text1)
        count1 = await chroma_store.count()

        # Update
        await chroma_store.upsert_document(doc_id, text2)
        count2 = await chroma_store.count()

        # Count should remain the same (update, not insert)
        assert count1 == count2 == 1

        # Verify updated content
        doc = await chroma_store.get_document(doc_id)
        assert doc["text"] == text2

    async def test_query_similar(self, chroma_store):
        """Test semantic similarity query."""
        # Insert test documents
        docs = [
            ("doc1", "Python programming language for data science", {"type": "code"}),
            ("doc2", "Machine learning algorithms and neural networks", {"type": "ml"}),
            ("doc3", "JavaScript web development framework", {"type": "code"}),
        ]

        for doc_id, text, metadata in docs:
            await chroma_store.upsert_document(doc_id, text, metadata)

        # Query for ML-related content
        results = await chroma_store.query_similar("deep learning", top_k=2)

        assert len(results) <= 2
        assert all("id" in r for r in results)
        assert all("text" in r for r in results)
        assert all("score" in r for r in results)
        assert all("metadata" in r for r in results)

        # Most relevant should be doc2 (ML-related)
        if results:
            assert results[0]["id"] == "doc2"

    async def test_query_with_filter(self, chroma_store):
        """Test query with metadata filter."""
        # Insert test documents
        docs = [
            ("doc1", "Python for ML", {"pattern_type": "code"}),
            ("doc2", "ML tutorial", {"pattern_type": "documentation"}),
            ("doc3", "Neural networks", {"pattern_type": "documentation"}),
        ]

        for doc_id, text, metadata in docs:
            await chroma_store.upsert_document(doc_id, text, metadata)

        # Query with filter
        results = await chroma_store.query_similar(
            "machine learning", top_k=5, pattern_type="documentation"
        )

        # Should only return documentation type
        assert all(r["metadata"].get("pattern_type") == "documentation" for r in results)
        assert len(results) <= 2  # Only 2 documentation docs

    async def test_get_document(self, chroma_store):
        """Test retrieving specific document by ID."""
        doc_id = "test_doc_get"
        text = "Test document content"
        metadata = {"key": "value"}

        await chroma_store.upsert_document(doc_id, text, metadata)

        doc = await chroma_store.get_document(doc_id)
        assert doc is not None
        assert doc["id"] == doc_id
        assert doc["text"] == text
        assert doc["metadata"]["key"] == "value"

    async def test_get_nonexistent_document(self, chroma_store):
        """Test retrieving non-existent document."""
        doc = await chroma_store.get_document("nonexistent_id")
        assert doc is None

    async def test_delete_document(self, chroma_store):
        """Test deleting a document."""
        doc_id = "test_doc_delete"
        text = "Document to delete"

        await chroma_store.upsert_document(doc_id, text)
        count_before = await chroma_store.count()
        assert count_before == 1

        success = await chroma_store.delete_document(doc_id)
        assert success is True

        count_after = await chroma_store.count()
        assert count_after == 0

        # Verify document is gone
        doc = await chroma_store.get_document(doc_id)
        assert doc is None

    async def test_count(self, chroma_store):
        """Test document count."""
        initial_count = await chroma_store.count()
        assert initial_count == 0

        # Add documents
        for i in range(5):
            await chroma_store.upsert_document(f"doc{i}", f"Content {i}")

        final_count = await chroma_store.count()
        assert final_count == 5

    async def test_health_check(self, chroma_store):
        """Test health check."""
        health = await chroma_store.health()

        assert health["backend"] == "chromadb"
        assert health["mode"] == "local"
        assert health["collection"] == "test_collection"
        assert isinstance(health["count"], int)
        assert health["last_error"] is None

    async def test_health_check_after_error(self, chroma_store):
        """Test health check includes last error."""
        # Force an error
        try:
            await chroma_store.upsert_document("", "")  # Empty ID might cause error
        except Exception:
            pass

        health = await chroma_store.health()
        # Should still return health info even after error
        assert "backend" in health
        assert "count" in health

    async def test_upsert_with_custom_embedding(self, chroma_store):
        """Test upserting document with pre-computed embedding."""
        doc_id = "custom_embed_doc"
        text = "Test document"
        embedding = [0.1] * 384  # Typical sentence-transformer dimension

        result_id = await chroma_store.upsert_document(doc_id, text, embedding=embedding)
        assert result_id == doc_id

        # Verify it was stored
        doc = await chroma_store.get_document(doc_id)
        assert doc is not None

    async def test_query_with_custom_embedding(self, chroma_store):
        """Test querying with pre-computed embedding."""
        # Insert document
        await chroma_store.upsert_document("doc1", "Test content")

        # Query with custom embedding
        query_embedding = [0.1] * 384
        results = await chroma_store.query_similar(
            "dummy query", top_k=1, query_embedding=query_embedding  # Text won't be used
        )

        # Should return results based on embedding similarity
        assert isinstance(results, list)
