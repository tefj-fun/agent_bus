"""API endpoints for memory pattern management."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

from ...config import settings
from ...infrastructure.postgres_client import postgres_client
from ...memory import create_memory_store, HybridMemoryStore
from ...memory.base import MemoryStoreBase


router = APIRouter(prefix="/api/patterns", tags=["patterns"])


class StorePatternRequest(BaseModel):
    """Request to store a pattern."""

    text: str = Field(..., description="Pattern content")
    pattern_type: str = Field("general", description="Pattern type (prd, architecture, code, etc.)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    success_score: float = Field(0.0, ge=0.0, le=1.0, description="Success score (0-1)")
    pattern_id: Optional[str] = Field(None, description="Optional custom ID")


class QueryPatternsRequest(BaseModel):
    """Request to query patterns."""

    query: str = Field(..., description="Search query")
    top_k: int = Field(5, gt=0, le=20, description="Number of results")
    pattern_type: Optional[str] = Field(None, description="Filter by pattern type")


class SuggestTemplatesRequest(BaseModel):
    """Request for template suggestions."""

    requirements: str = Field(..., description="Project requirements")
    top_k: int = Field(3, gt=0, le=10, description="Number of suggestions")
    min_score: float = Field(0.5, ge=0.0, le=1.0, description="Minimum combined score")


_memory_store: Optional[MemoryStoreBase] = None
_memory_store_synced: bool = False


async def get_memory_store() -> MemoryStoreBase:
    """Get memory store instance (hybrid by default)."""
    global _memory_store, _memory_store_synced
    if _memory_store is None:
        pool = await postgres_client.get_pool()
        _memory_store = create_memory_store(
            settings.memory_backend,
            db_pool=pool,
            pattern_type_default="general",
            collection_name=settings.chroma_collection_name,
            persist_directory=settings.chroma_persist_directory,
            host=settings.chroma_host,
            port=settings.chroma_port,
        )

    if (
        settings.memory_auto_sync
        and not _memory_store_synced
        and isinstance(_memory_store, HybridMemoryStore)
    ):
        try:
            await _memory_store.sync_from_postgres()
        finally:
            _memory_store_synced = True

    return _memory_store


@router.post("/store")
async def store_pattern(
    request: StorePatternRequest,
    store: MemoryStoreBase = Depends(get_memory_store),
):
    """
    Store a new pattern or update existing one.

    Args:
        request: Pattern data

    Returns:
        Stored pattern info
    """
    try:
        # Prepare metadata
        metadata = request.metadata or {}
        metadata.update(
            {
                "pattern_type": request.pattern_type,
                "success_score": str(request.success_score),
                "usage_count": metadata.get("usage_count", "0"),
            }
        )

        # Generate ID if not provided
        pattern_id = request.pattern_id
        if not pattern_id:
            import uuid

            pattern_id = f"pattern_{uuid.uuid4().hex[:12]}"

        # Store pattern
        stored_id = await store.upsert_document(pattern_id, request.text, metadata)

        return {
            "status": "success",
            "pattern_id": stored_id,
            "pattern_type": request.pattern_type,
            "success_score": request.success_score,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/query")
async def query_patterns(
    request: QueryPatternsRequest,
    store: MemoryStoreBase = Depends(get_memory_store),
):
    """
    Query for similar patterns using semantic search.

    Args:
        request: Query parameters

    Returns:
        List of similar patterns
    """
    try:
        filters = {"pattern_type": request.pattern_type} if request.pattern_type else None
        results = await store.search(
            query=request.query,
            top_k=request.top_k,
            filters=filters,
        )

        return {
            "status": "success",
            "query": request.query,
            "pattern_type": request.pattern_type,
            "results": results,
            "count": len(results),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/suggest")
async def suggest_templates(
    request: SuggestTemplatesRequest,
    store: MemoryStoreBase = Depends(get_memory_store),
):
    """
    Suggest templates based on requirements.

    Args:
        request: Requirements and parameters

    Returns:
        List of suggested templates
    """
    try:
        # Query for similar templates
        candidates = await store.search(
            query=request.requirements,
            top_k=request.top_k * 2,
            filters={"pattern_type": "template"},
        )

        # Rank by combined score
        suggestions = []
        for candidate in candidates:
            similarity_score = candidate.get("score", 0.0)
            metadata = candidate.get("metadata", {})
            success_score = float(metadata.get("success_score", 0.5))
            usage_count = int(metadata.get("usage_count", 0))

            # Combined ranking: 70% similarity, 30% success
            combined_score = similarity_score * 0.7 + success_score * 0.3

            if combined_score >= request.min_score:
                suggestions.append(
                    {
                        "pattern_id": candidate.get("id"),
                        "text": candidate.get("text", "")[:500],  # Truncate
                        "similarity_score": round(similarity_score, 3),
                        "success_score": round(success_score, 3),
                        "usage_count": usage_count,
                        "combined_score": round(combined_score, 3),
                        "metadata": metadata,
                    }
                )

        # Sort by combined score
        suggestions.sort(key=lambda x: x["combined_score"], reverse=True)
        suggestions = suggestions[: request.top_k]

        return {
            "status": "success",
            "requirements": request.requirements,
            "suggestions": suggestions,
            "count": len(suggestions),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/types")
async def list_pattern_types(store: MemoryStoreBase = Depends(get_memory_store)):
    """
    List available pattern types with counts.

    Returns:
        Pattern type statistics
    """
    try:
        # Get all documents
        # Note: ChromaDB doesn't have a direct "list all" API, so we query with empty embedding
        # This is a simplified implementation
        health = await store.health()

        # Return common pattern types (would need full scan to get actual counts)
        common_types = [
            "prd",
            "architecture",
            "code",
            "test",
            "documentation",
            "template",
            "general",
        ]

        return {
            "status": "success",
            "total_patterns": health.get("count", 0),
            "common_types": common_types,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
async def patterns_health(store: MemoryStoreBase = Depends(get_memory_store)):
    """
    Get health status of pattern storage system.

    Returns:
        Health information
    """
    try:
        health = await store.health()
        return {
            "status": "success",
            **health,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/sync")
async def sync_patterns(store: MemoryStoreBase = Depends(get_memory_store)):
    """Backfill vector index from Postgres memory_patterns (hybrid backend only)."""
    if hasattr(store, "sync_from_postgres"):
        migrated = await store.sync_from_postgres()
        return {"status": "success", "migrated": migrated}
    raise HTTPException(status_code=400, detail="Sync not supported for this backend")


@router.post("/{pattern_id}/increment-usage")
async def increment_usage(
    pattern_id: str,
    store: MemoryStoreBase = Depends(get_memory_store),
):
    """
    Increment usage count for a pattern.

    Args:
        pattern_id: Pattern identifier

    Returns:
        Updated usage count
    """
    try:
        # Get document
        doc = await store.retrieve(pattern_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")

        # Increment usage count
        metadata = doc.get("metadata", {})
        usage_count = int(metadata.get("usage_count", 0)) + 1
        metadata["usage_count"] = str(usage_count)

        # Update document
        await store.upsert_document(pattern_id, doc["text"], metadata)

        return {
            "status": "success",
            "pattern_id": pattern_id,
            "usage_count": usage_count,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{pattern_id}")
async def get_pattern(
    pattern_id: str,
    store: MemoryStoreBase = Depends(get_memory_store),
):
    """
    Get a specific pattern by ID.

    Args:
        pattern_id: Pattern identifier

    Returns:
        Pattern data
    """
    try:
        doc = await store.retrieve(pattern_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")

        return {
            "status": "success",
            "pattern": doc,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{pattern_id}")
async def delete_pattern(
    pattern_id: str,
    store: MemoryStoreBase = Depends(get_memory_store),
):
    """
    Delete a pattern.

    Args:
        pattern_id: Pattern identifier

    Returns:
        Deletion status
    """
    try:
        success = await store.delete(pattern_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")

        return {
            "status": "success",
            "pattern_id": pattern_id,
            "deleted": True,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
