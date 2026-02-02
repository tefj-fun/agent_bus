"""Embedding generation using sentence-transformers for semantic search."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """Generate vector embeddings for text using sentence-transformers."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: Optional[str] = None,
        device: Optional[str] = None,
    ):
        """
        Initialize embedding generator.

        Args:
            model_name: Sentence-transformer model name (default: all-MiniLM-L6-v2, 384 dims)
            cache_dir: Directory to cache model files
            device: Device to use ('cpu', 'cuda', or None for auto-detection)
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.device = device

        # Initialize model
        self.model = SentenceTransformer(
            model_name,
            cache_folder=cache_dir,
            device=device,
        )

        # Embedding cache (in-memory for this session)
        self._cache: Dict[str, List[float]] = {}

        # Get embedding dimension
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def get_embedding_dimension(self) -> int:
        """Get the dimensionality of embeddings from this model."""
        return self.embedding_dim

    def _compute_cache_key(self, text: str) -> str:
        """Compute cache key for text."""
        return hashlib.sha256(text.encode()).hexdigest()

    def generate(
        self,
        text: str,
        use_cache: bool = True,
        normalize: bool = True,
    ) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text
            use_cache: Whether to use cached embeddings
            normalize: Whether to normalize embeddings to unit length

        Returns:
            Embedding vector as list of floats
        """
        if not text:
            # Return zero vector for empty text
            return [0.0] * self.embedding_dim

        # Check cache
        if use_cache:
            cache_key = self._compute_cache_key(text)
            if cache_key in self._cache:
                return self._cache[cache_key]

        # Generate embedding
        embedding = self.model.encode(
            text,
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )

        # Convert to list
        embedding_list = embedding.tolist()

        # Cache result
        if use_cache:
            cache_key = self._compute_cache_key(text)
            self._cache[cache_key] = embedding_list

        return embedding_list

    def generate_batch(
        self,
        texts: List[str],
        use_cache: bool = True,
        normalize: bool = True,
        batch_size: int = 32,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of input texts
            use_cache: Whether to use cached embeddings
            normalize: Whether to normalize embeddings
            batch_size: Batch size for encoding

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        embeddings = []
        texts_to_encode = []
        indices_to_encode = []

        # Check cache
        for i, text in enumerate(texts):
            if not text:
                embeddings.append([0.0] * self.embedding_dim)
                continue

            if use_cache:
                cache_key = self._compute_cache_key(text)
                if cache_key in self._cache:
                    embeddings.append(self._cache[cache_key])
                    continue

            # Need to encode this text
            texts_to_encode.append(text)
            indices_to_encode.append(i)
            embeddings.append(None)  # Placeholder

        # Encode uncached texts
        if texts_to_encode:
            batch_embeddings = self.model.encode(
                texts_to_encode,
                normalize_embeddings=normalize,
                show_progress_bar=False,
                batch_size=batch_size,
            )

            # Fill in results and cache
            for idx, embedding in zip(indices_to_encode, batch_embeddings):
                embedding_list = embedding.tolist()
                embeddings[idx] = embedding_list

                if use_cache:
                    cache_key = self._compute_cache_key(texts[idx])
                    self._cache[cache_key] = embedding_list

        return embeddings

    def chunk_text(
        self,
        text: str,
        max_chunk_length: int = 500,
        overlap: int = 50,
    ) -> List[str]:
        """
        Split long text into overlapping chunks.

        Args:
            text: Input text to chunk
            max_chunk_length: Maximum characters per chunk
            overlap: Overlap characters between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= max_chunk_length:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + max_chunk_length, len(text))

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings in the last 20% of chunk
                search_start = max(start, end - int(max_chunk_length * 0.2))
                sentence_end = max(
                    text.rfind(". ", search_start, end),
                    text.rfind("! ", search_start, end),
                    text.rfind("? ", search_start, end),
                    text.rfind("\n", search_start, end),
                )
                if sentence_end > start:
                    end = sentence_end + 1

            chunks.append(text[start:end].strip())
            start = end - overlap if end < len(text) else end

        return chunks

    def generate_chunked(
        self,
        text: str,
        max_chunk_length: int = 500,
        overlap: int = 50,
        aggregation: str = "mean",
    ) -> Tuple[List[float], List[str]]:
        """
        Generate embedding for long text by chunking and aggregating.

        Args:
            text: Input text (potentially long)
            max_chunk_length: Maximum characters per chunk
            overlap: Overlap characters between chunks
            aggregation: How to aggregate chunk embeddings ('mean', 'max', 'first')

        Returns:
            Tuple of (aggregated_embedding, list_of_chunks)
        """
        # Chunk the text
        chunks = self.chunk_text(text, max_chunk_length, overlap)

        if not chunks:
            return [0.0] * self.embedding_dim, []

        # Generate embeddings for chunks
        chunk_embeddings = self.generate_batch(chunks)

        # Aggregate embeddings
        if aggregation == "mean":
            # Average all chunk embeddings
            aggregated = [
                sum(emb[i] for emb in chunk_embeddings) / len(chunk_embeddings)
                for i in range(self.embedding_dim)
            ]
        elif aggregation == "max":
            # Take max value per dimension
            aggregated = [
                max(emb[i] for emb in chunk_embeddings) for i in range(self.embedding_dim)
            ]
        elif aggregation == "first":
            # Use first chunk only
            aggregated = chunk_embeddings[0]
        else:
            raise ValueError(f"Unknown aggregation method: {aggregation}")

        return aggregated, chunks

    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()

    def cache_size(self) -> int:
        """Get number of cached embeddings."""
        return len(self._cache)

    def get_info(self) -> Dict[str, Any]:
        """Get information about the embedding generator."""
        return {
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "device": str(self.model.device),
            "cache_size": len(self._cache),
        }
