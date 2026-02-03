"""API routes for memory store operations."""

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...infrastructure.postgres_client import postgres_client
from ...memory import create_memory_store
from ...config import settings


router = APIRouter()


class MemoryUpsertRequest(BaseModel):
    doc_id: Optional[str] = None
    text: str
    metadata: Optional[Dict[str, Any]] = None


class MemoryQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    pattern_type: Optional[str] = None


@router.get("/health")
async def memory_health():
    """Health check for memory store."""
    try:
        pool = await postgres_client.get_pool()
        store = create_memory_store(
            settings.memory_backend,
            db_pool=pool,
            collection_name=settings.chroma_collection_name,
            persist_directory=settings.chroma_persist_directory,
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        return await store.health()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/upsert")
async def memory_upsert(request: MemoryUpsertRequest):
    """Upsert a memory document."""
    try:
        pool = await postgres_client.get_pool()
        store = create_memory_store(
            settings.memory_backend,
            db_pool=pool,
            collection_name=settings.chroma_collection_name,
            persist_directory=settings.chroma_persist_directory,
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        doc_id = request.doc_id or f"mem_{uuid.uuid4().hex[:12]}"
        stored_id = await store.upsert_document(
            doc_id=doc_id,
            text=request.text,
            metadata=request.metadata or {},
        )
        return {"doc_id": stored_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/query")
async def memory_query(request: MemoryQueryRequest):
    """Query similar memory documents."""
    try:
        pool = await postgres_client.get_pool()
        store = create_memory_store(
            settings.memory_backend,
            db_pool=pool,
            collection_name=settings.chroma_collection_name,
            persist_directory=settings.chroma_persist_directory,
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        results = await store.query_similar(
            query=request.query,
            top_k=request.top_k,
            pattern_type=request.pattern_type,
        )
        return {"query": request.query, "results": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
