"""Tests for embedding generator."""

import pytest
from src.memory.embedding_generator import EmbeddingGenerator

# Skip in CI - requires sentence-transformers model download
pytestmark = pytest.mark.skipif(True, reason="Requires model download - run manually")


@pytest.fixture
def embedding_gen():
    """Create embedding generator instance."""
    return EmbeddingGenerator(model_name="all-MiniLM-L6-v2")


class TestEmbeddingGenerator:
    """Test embedding generation functionality."""

    def test_init(self, embedding_gen):
        """Test initialization."""
        assert embedding_gen.model_name == "all-MiniLM-L6-v2"
        assert embedding_gen.embedding_dim == 384  # all-MiniLM-L6-v2 dimension
        assert embedding_gen.cache_size() == 0

    def test_get_embedding_dimension(self, embedding_gen):
        """Test getting embedding dimension."""
        dim = embedding_gen.get_embedding_dimension()
        assert dim == 384
        assert isinstance(dim, int)

    def test_generate_single(self, embedding_gen):
        """Test generating single embedding."""
        text = "This is a test sentence about machine learning."
        embedding = embedding_gen.generate(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    def test_generate_empty_text(self, embedding_gen):
        """Test generating embedding for empty text."""
        embedding = embedding_gen.generate("")
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)

    def test_cache_hit(self, embedding_gen):
        """Test that cache is used on repeated calls."""
        text = "Machine learning is fascinating."

        # First call - should cache
        embedding1 = embedding_gen.generate(text, use_cache=True)
        cache_size_1 = embedding_gen.cache_size()

        # Second call - should hit cache
        embedding2 = embedding_gen.generate(text, use_cache=True)
        cache_size_2 = embedding_gen.cache_size()

        assert embedding1 == embedding2
        assert cache_size_1 == 1
        assert cache_size_2 == 1  # Should not increase

    def test_cache_disabled(self, embedding_gen):
        """Test with caching disabled."""
        text = "Test sentence for cache test."

        embedding1 = embedding_gen.generate(text, use_cache=False)
        cache_size = embedding_gen.cache_size()

        assert isinstance(embedding1, list)
        assert cache_size == 0  # Should not cache

    def test_generate_batch(self, embedding_gen):
        """Test batch embedding generation."""
        texts = [
            "Python programming",
            "Machine learning",
            "Data science",
        ]

        embeddings = embedding_gen.generate_batch(texts)

        assert len(embeddings) == 3
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) == 384 for emb in embeddings)

    def test_generate_batch_with_empty(self, embedding_gen):
        """Test batch generation with empty strings."""
        texts = ["Valid text", "", "Another text"]

        embeddings = embedding_gen.generate_batch(texts)

        assert len(embeddings) == 3
        # Empty text should give zero vector
        assert all(x == 0.0 for x in embeddings[1])

    def test_generate_batch_caching(self, embedding_gen):
        """Test that batch generation uses cache."""
        texts = ["Text A", "Text B", "Text A"]  # Text A repeated

        initial_cache_size = embedding_gen.cache_size()
        embeddings = embedding_gen.generate_batch(texts, use_cache=True)
        final_cache_size = embedding_gen.cache_size()

        # Should cache only unique texts
        assert final_cache_size == initial_cache_size + 2
        # First and third should be identical
        assert embeddings[0] == embeddings[2]

    def test_chunk_text_short(self, embedding_gen):
        """Test chunking short text."""
        text = "Short text that doesn't need chunking."
        chunks = embedding_gen.chunk_text(text, max_chunk_length=500)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_long(self, embedding_gen):
        """Test chunking long text."""
        text = "A. " * 300  # Create long text
        chunks = embedding_gen.chunk_text(text, max_chunk_length=100, overlap=20)

        assert len(chunks) > 1
        assert all(len(chunk) <= 120 for chunk in chunks)  # With some tolerance

    def test_chunk_text_sentence_boundary(self, embedding_gen):
        """Test that chunking respects sentence boundaries."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        chunks = embedding_gen.chunk_text(text, max_chunk_length=40, overlap=5)

        # Should break at sentence boundaries when possible
        assert len(chunks) > 1
        # Most chunks should end with punctuation
        assert sum(chunk.rstrip().endswith(".") for chunk in chunks) >= len(chunks) - 1

    def test_chunk_text_overlap(self, embedding_gen):
        """Test that chunks have proper overlap."""
        text = "word " * 100  # Simple repeated text
        chunks = embedding_gen.chunk_text(text, max_chunk_length=50, overlap=10)

        if len(chunks) > 1:
            # Check that consecutive chunks share some content
            for i in range(len(chunks) - 1):
                # There should be some overlap in words
                words1 = set(chunks[i].split())
                words2 = set(chunks[i + 1].split())
                assert len(words1 & words2) > 0

    def test_generate_chunked_short(self, embedding_gen):
        """Test chunked generation with short text."""
        text = "Short text."
        embedding, chunks = embedding_gen.generate_chunked(text, max_chunk_length=500)

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_generate_chunked_long(self, embedding_gen):
        """Test chunked generation with long text."""
        text = "This is a sentence. " * 50  # Long text
        embedding, chunks = embedding_gen.generate_chunked(text, max_chunk_length=100, overlap=20)

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert len(chunks) > 1
        # All values should be non-zero (aggregated from multiple chunks)
        assert any(x != 0.0 for x in embedding)

    def test_generate_chunked_aggregation_mean(self, embedding_gen):
        """Test chunked generation with mean aggregation."""
        text = "sentence " * 100
        embedding, chunks = embedding_gen.generate_chunked(text, aggregation="mean")

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert len(chunks) > 1

    def test_generate_chunked_aggregation_max(self, embedding_gen):
        """Test chunked generation with max aggregation."""
        text = "sentence " * 100
        embedding, chunks = embedding_gen.generate_chunked(text, aggregation="max")

        assert isinstance(embedding, list)
        assert len(embedding) == 384

    def test_generate_chunked_aggregation_first(self, embedding_gen):
        """Test chunked generation with first-chunk aggregation."""
        text = "sentence " * 100
        embedding, chunks = embedding_gen.generate_chunked(text, aggregation="first")

        # Should equal the embedding of the first chunk
        first_chunk_embedding = embedding_gen.generate(chunks[0])
        assert embedding == first_chunk_embedding

    def test_generate_chunked_invalid_aggregation(self, embedding_gen):
        """Test chunked generation with invalid aggregation method."""
        text = "Test text"
        with pytest.raises(ValueError, match="Unknown aggregation method"):
            embedding_gen.generate_chunked(text, aggregation="invalid")

    def test_clear_cache(self, embedding_gen):
        """Test clearing the cache."""
        text = "Test caching."
        embedding_gen.generate(text, use_cache=True)
        assert embedding_gen.cache_size() > 0

        embedding_gen.clear_cache()
        assert embedding_gen.cache_size() == 0

    def test_get_info(self, embedding_gen):
        """Test getting generator info."""
        info = embedding_gen.get_info()

        assert info["model_name"] == "all-MiniLM-L6-v2"
        assert info["embedding_dim"] == 384
        assert "device" in info
        assert "cache_size" in info

    def test_semantic_similarity(self, embedding_gen):
        """Test that semantically similar texts have similar embeddings."""
        text1 = "Machine learning is a subset of artificial intelligence."
        text2 = "AI includes machine learning as a subfield."
        text3 = "The weather is sunny today."

        emb1 = embedding_gen.generate(text1)
        emb2 = embedding_gen.generate(text2)
        emb3 = embedding_gen.generate(text3)

        # Compute cosine similarity
        def cosine_sim(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(y * y for y in b) ** 0.5
            return dot / (norm_a * norm_b)

        sim_12 = cosine_sim(emb1, emb2)
        sim_13 = cosine_sim(emb1, emb3)

        # Semantically similar texts should have higher similarity
        assert sim_12 > sim_13
