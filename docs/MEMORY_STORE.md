# Memory Store System

The agent_bus memory system provides a unified interface for storing and querying project memory with support for multiple backend implementations.

## Overview

The memory store system consists of:

1. **Abstract Interface** (`MemoryStoreBase`) - Defines the contract all backends must implement
2. **Backend Implementations**:
   - `PostgresMemoryStore` - TF-IDF keyword search backed by PostgreSQL
   - `ChromaDBMemoryStore` - Vector similarity search backed by ChromaDB
   - `InMemoryStore` - In-memory storage for testing
3. **Factory/Registry** - For backend selection and instantiation

## Quick Start

### Using the Factory (Recommended)

```python
from src.memory import create_memory_store

# Postgres backend (default)
store = create_memory_store("postgres", db_pool=pool)

# ChromaDB backend
store = create_memory_store("chromadb", collection_name="my_memory")

# In-memory backend (for testing)
store = create_memory_store("in-memory")
```

### Direct Instantiation

```python
from src.memory import PostgresMemoryStore, ChromaDBMemoryStore, InMemoryStore

# Postgres
store = PostgresMemoryStore(db_pool=pool)

# ChromaDB
store = ChromaDBMemoryStore(
    collection_name="agent_bus_memory",
    persist_directory="/data/chroma"
)

# In-memory
store = InMemoryStore()
```

## Core Operations

All memory store backends implement the same interface:

### Store a Document

```python
doc_id = await store.store(
    doc_id="prd-123",
    text="Product requirements document content...",
    metadata={
        "pattern_type": "prd",
        "project_id": "proj-456",
        "created_by": "prd_agent"
    }
)
```

### Retrieve by ID

```python
doc = await store.retrieve("prd-123")
if doc:
    print(doc["id"])        # "prd-123"
    print(doc["text"])      # Document content
    print(doc["metadata"])  # Metadata dict
```

### Search for Similar Documents

```python
# Search all documents
results = await store.search(
    query="payment processing requirements",
    top_k=5
)

# Search with filters
results = await store.search(
    query="payment processing",
    top_k=5,
    filters={"pattern_type": "prd"}
)

for result in results:
    print(f"{result['id']}: score={result['score']:.3f}")
    print(result["text"])
    print(result["metadata"])
```

### Update a Document

```python
# Update text only
await store.update("prd-123", text="Updated content...")

# Update metadata only (merges with existing)
await store.update("prd-123", metadata={"version": 2})

# Update both
await store.update(
    "prd-123",
    text="Updated content...",
    metadata={"version": 2, "updated_by": "human"}
)
```

### Delete a Document

```python
success = await store.delete("prd-123")
```

### Count Documents

```python
# Count all
total = await store.count()

# Count with filter
prd_count = await store.count(filters={"pattern_type": "prd"})
```

### Health Check

```python
health = await store.health()
print(health["backend"])     # "postgres_tfidf", "chromadb", etc.
print(health["status"])      # "healthy" or "error"
print(health["count"])       # Total document count
print(health["last_error"])  # Last error message or None
```

### Clear Documents

```python
# Clear all documents (use with caution!)
deleted = await store.clear()

# Clear documents matching filter
deleted = await store.clear(filters={"pattern_type": "test"})
```

## Backend Comparison

### PostgresMemoryStore

**Strengths:**
- Integrated with existing PostgreSQL database
- No additional dependencies
- Good for keyword-based search
- Transactional consistency
- Excellent for structured metadata queries

**Weaknesses:**
- TF-IDF search is less sophisticated than vector embeddings
- Not ideal for semantic similarity
- Performance degrades with very large datasets

**Best for:**
- Exact keyword matching
- When you already have Postgres
- Structured metadata filtering
- Transactional guarantees

**Configuration:**
```python
store = PostgresMemoryStore(
    db_pool=pool,
    pattern_type_default="document"  # Default pattern type
)
```

### ChromaDBMemoryStore

**Strengths:**
- Vector similarity search (semantic understanding)
- Excellent for finding conceptually similar content
- Built-in embedding generation
- Scales well to large datasets
- Persistent storage option

**Weaknesses:**
- Requires chromadb package: `pip install chromadb`
- Additional storage overhead for vectors
- Slower for exact keyword matching

**Best for:**
- Semantic similarity search
- Pattern recognition across memory
- "Find similar PRDs/plans/architectures"
- When keyword matching isn't enough

**Configuration:**
```python
# In-memory
store = ChromaDBMemoryStore(collection_name="agent_bus_memory")

# Persistent
store = ChromaDBMemoryStore(
    collection_name="agent_bus_memory",
    persist_directory="/data/chroma"
)

# Custom embedding function
from chromadb.utils import embedding_functions
ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
store = ChromaDBMemoryStore(
    collection_name="agent_bus_memory",
    embedding_function=ef
)
```

### InMemoryStore

**Strengths:**
- No external dependencies
- Fast (everything in RAM)
- Perfect for testing
- Simple TF-IDF search

**Weaknesses:**
- Data lost on process restart
- Limited by available RAM
- Not suitable for production

**Best for:**
- Unit testing
- Development/debugging
- Temporary storage
- CI/CD test suites

**Configuration:**
```python
store = InMemoryStore()  # No configuration needed
```

## Backend Selection Guide

Choose your backend based on requirements:

| Requirement | Recommended Backend |
|-------------|-------------------|
| Production keyword search | PostgresMemoryStore |
| Production semantic search | ChromaDBMemoryStore |
| Testing/development | InMemoryStore |
| Exact metadata filtering | PostgresMemoryStore |
| "Find similar patterns" | ChromaDBMemoryStore |
| Already using Postgres | PostgresMemoryStore |
| Want simplest setup | InMemoryStore |
| Need persistence | Postgres or ChromaDB (persistent) |

## Registry and Custom Backends

### List Available Backends

```python
from src.memory import MemoryStoreRegistry

backends = MemoryStoreRegistry.list_backends()
# ['chroma', 'chromadb', 'in-memory', 'memory', 'postgres']
```

### Check Backend Availability

```python
if MemoryStoreRegistry.is_available("chromadb"):
    store = create_memory_store("chromadb")
else:
    store = create_memory_store("postgres", db_pool=pool)
```

### Register Custom Backend

```python
from src.memory import MemoryStoreBase, MemoryStoreRegistry

class RedisMemoryStore(MemoryStoreBase):
    """Custom Redis-backed memory store."""
    
    async def store(self, doc_id, text, metadata=None):
        # Implementation...
        pass
    
    # Implement other required methods...

# Register it
MemoryStoreRegistry.register("redis", RedisMemoryStore)

# Use it
store = create_memory_store("redis", redis_url="redis://localhost")
```

## Backward Compatibility

The system maintains backward compatibility with the original `MemoryStore` class:

```python
# Old code still works
from src.memory import MemoryStore

store = MemoryStore(db_pool=pool)
await store.upsert_document("doc1", "content", {"type": "prd"})
results = await store.query_similar("query", pattern_type="prd")
```

New code should use the unified interface:

```python
# New code
from src.memory import create_memory_store

store = create_memory_store("postgres", db_pool=pool)
await store.store("doc1", "content", {"pattern_type": "prd"})
results = await store.search("query", filters={"pattern_type": "prd"})
```

## Migration Guide

### From Old MemoryStore to New Interface

**Before:**
```python
from src.memory.store import MemoryStore

store = MemoryStore(db_pool=pool)
await store.upsert_document(doc_id, text, metadata)
results = await store.query_similar(query, top_k=5, pattern_type="prd")
count = await store.count()
```

**After:**
```python
from src.memory import PostgresMemoryStore

store = PostgresMemoryStore(db_pool=pool)
await store.store(doc_id, text, metadata)
results = await store.search(query, top_k=5, filters={"pattern_type": "prd"})
count = await store.count()
```

Or use the factory:
```python
from src.memory import create_memory_store

store = create_memory_store("postgres", db_pool=pool)
# Same API as above
```

## Testing

### Unit Tests

```python
import pytest
from src.memory import InMemoryStore

@pytest.mark.asyncio
async def test_my_feature():
    # Use in-memory store for fast, isolated tests
    store = InMemoryStore()
    
    await store.store("doc1", "test content", {"type": "test"})
    doc = await store.retrieve("doc1")
    
    assert doc["text"] == "test content"
    
    # Cleanup (optional, each test gets fresh instance anyway)
    await store.clear()
```

### Integration Tests

```python
import pytest
from src.memory import create_memory_store

@pytest.mark.asyncio
async def test_with_real_backend(db_pool):
    # Use real Postgres in integration tests
    store = create_memory_store("postgres", db_pool=db_pool)
    
    await store.store("doc1", "integration test", {"env": "test"})
    results = await store.search("integration", top_k=1)
    
    assert len(results) > 0
    
    # Cleanup test data
    await store.clear(filters={"env": "test"})
```

## Performance Considerations

### PostgresMemoryStore

- TF-IDF computation is O(n) where n = number of documents
- Filter by `pattern_type` first to reduce search space
- Consider indexes on metadata fields for large datasets
- Database connection pooling is important

### ChromaDBMemoryStore

- First query may be slower (embedding generation)
- Subsequent queries are fast (vector similarity is efficient)
- Consider batching large imports
- Persistent mode has disk I/O overhead
- Memory usage scales with collection size

### InMemoryStore

- Very fast (everything in RAM)
- Limited by available memory
- Best for < 10,000 documents in tests

## Environment Configuration

Set default backend via environment variable:

```bash
# .env
MEMORY_STORE_BACKEND=chromadb
MEMORY_STORE_COLLECTION=agent_bus_memory
CHROMA_PERSIST_DIR=/data/chroma
```

```python
import os
from src.memory import create_memory_store

backend = os.getenv("MEMORY_STORE_BACKEND", "postgres")

if backend == "chromadb":
    store = create_memory_store(
        "chromadb",
        collection_name=os.getenv("MEMORY_STORE_COLLECTION"),
        persist_directory=os.getenv("CHROMA_PERSIST_DIR")
    )
else:
    store = create_memory_store("postgres", db_pool=db_pool)
```

## Troubleshooting

### ChromaDB Import Error

```
ImportError: chromadb is not installed
```

**Solution:** Install ChromaDB:
```bash
pip install chromadb
# or
poetry add chromadb
```

### Metadata Type Error with ChromaDB

ChromaDB only supports `str`, `int`, `float`, `bool` in metadata. Complex types are automatically converted to strings:

```python
# This works
await store.store("doc1", "text", {"count": 42, "name": "test"})

# This is automatically converted
await store.store("doc1", "text", {"data": {"nested": "dict"}})
# metadata becomes: {"data": "{'nested': 'dict'}"}
```

### Search Returns No Results

1. Check if documents are actually stored: `await store.count()`
2. Verify filters match metadata exactly
3. For ChromaDB, ensure query has semantic overlap with documents
4. For Postgres, use keyword overlap (TF-IDF)

## Future Enhancements

Planned features:

- [ ] ElasticsearchMemoryStore backend
- [ ] RedisMemoryStore backend (with RediSearch)
- [ ] Hybrid search (combine keyword + vector)
- [ ] Batch operations for better performance
- [ ] Async context manager support
- [ ] Query result caching
- [ ] Metadata schema validation
- [ ] Auto-migration between backends

## API Reference

See `src/memory/base.py` for complete interface documentation.

Key classes:
- `MemoryStoreBase` - Abstract base class
- `PostgresMemoryStore` - Postgres backend
- `ChromaDBMemoryStore` - ChromaDB backend
- `InMemoryStore` - In-memory backend
- `MemoryStoreRegistry` - Backend registry
- `create_memory_store()` - Factory function
