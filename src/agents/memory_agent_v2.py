"""Memory Agent v2 - Pattern storage and retrieval with ChromaDB."""

import json
import uuid
from typing import Any, Dict

from .base import BaseAgent, AgentResult, AgentTask
from ..memory.chroma_store import ChromaDBStore
from ..config import settings


class MemoryAgentV2(BaseAgent):
    """Agent specialized in pattern storage and retrieval using vector search."""

    def __init__(self, context):
        # Initialize ChromaDB store
        self.store = ChromaDBStore(
            collection_name="agent_bus_patterns",
            persist_directory=settings.chroma_persist_directory,
            auto_embed=True,
        )
        super().__init__(context)

    def get_agent_id(self) -> str:
        return "memory_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        return {
            "can_store_patterns": True,
            "can_query_patterns": True,
            "can_suggest_templates": True,
            "backend": "chromadb_vector",
            "supports_semantic_search": True,
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute memory operation based on task inputs."""
        try:
            await self.log_event("info", "Starting memory operation")

            action = str(task.input_data.get("action", "query")).lower()
            persist_artifact = task.input_data.get("persist_artifact", True)
            artifact_id = None

            if action in {"store", "upsert", "store_pattern"}:
                output = await self._store_pattern(task.input_data)
                if persist_artifact:
                    artifact_id = await self.save_artifact(
                        artifact_type="memory_record",
                        content=json.dumps(output, indent=2),
                        metadata=output.get("metadata", {}),
                    )

            elif action in {"query", "search", "query_patterns"}:
                output = await self._query_patterns(task.input_data)
                if persist_artifact:
                    artifact_id = await self.save_artifact(
                        artifact_type="memory_query",
                        content=json.dumps(output, indent=2),
                        metadata={"top_k": task.input_data.get("top_k", 5)},
                    )

            elif action in {"suggest", "suggest_templates"}:
                output = await self._suggest_templates(task.input_data)
                if persist_artifact:
                    artifact_id = await self.save_artifact(
                        artifact_type="template_suggestions",
                        content=json.dumps(output, indent=2),
                        metadata={"suggestions_count": len(output.get("suggestions", []))},
                    )

            elif action in {"increment_usage", "track_usage"}:
                output = await self._increment_usage(task.input_data)

            elif action in {"health", "status"}:
                output = await self.store.health()

            else:
                raise ValueError(f"Unknown action: {action}")

            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=output,
                artifacts=[artifact_id] if artifact_id else [],
                metadata={"backend": "chromadb"},
            )

            await self.notify_completion(result)
            return result

        except Exception as exc:
            await self.log_event("error", f"Memory operation failed: {exc}")
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                output={},
                artifacts=[],
                error=str(exc),
            )
            await self.notify_completion(result)
            return result

    async def _store_pattern(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a pattern with metadata."""
        text = input_data.get("text") or input_data.get("document") or input_data.get("content")
        if not text:
            raise ValueError("Pattern storage requires 'text', 'document', or 'content' field")

        doc_id = input_data.get("id") or f"pattern_{uuid.uuid4().hex[:12]}"
        
        # Prepare metadata
        metadata = input_data.get("metadata") or {}
        pattern_type = input_data.get("pattern_type") or metadata.get("pattern_type", "general")
        success_score = float(input_data.get("success_score", metadata.get("success_score", 0.0)))
        usage_count = int(input_data.get("usage_count", metadata.get("usage_count", 0)))

        # Build enriched metadata
        full_metadata = {
            "pattern_type": pattern_type,
            "success_score": str(success_score),
            "usage_count": str(usage_count),
            **{k: str(v) for k, v in metadata.items() if k not in ["pattern_type", "success_score", "usage_count"]},
        }

        # Store in ChromaDB
        stored_id = await self.store.upsert_document(doc_id, text, full_metadata)

        await self.log_event("info", f"Stored pattern {stored_id} (type: {pattern_type})")

        return {
            "action": "store_pattern",
            "pattern_id": stored_id,
            "pattern_type": pattern_type,
            "success_score": success_score,
            "backend": "chromadb",
        }

    async def _query_patterns(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Query for similar patterns."""
        query = input_data.get("query") or input_data.get("text")
        if not query:
            raise ValueError("Pattern query requires 'query' or 'text' field")

        top_k = int(input_data.get("top_k", 5))
        pattern_type = input_data.get("pattern_type")

        # Query ChromaDB
        results = await self.store.query_similar(query, top_k, pattern_type)

        await self.log_event("info", f"Found {len(results)} similar patterns for query")

        return {
            "action": "query_patterns",
            "query": query,
            "pattern_type": pattern_type,
            "results": results,
            "count": len(results),
            "backend": "chromadb",
        }

    async def _suggest_templates(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest templates based on requirements."""
        query = input_data.get("query") or input_data.get("requirements") or input_data.get("text")
        if not query:
            raise ValueError("Template suggestion requires 'query', 'requirements', or 'text' field")

        top_k = int(input_data.get("top_k", 3))
        min_score = float(input_data.get("min_score", 0.5))

        # Query for similar patterns
        candidates = await self.store.query_similar(query, top_k=top_k * 2, pattern_type="template")

        # Rank by combined score (similarity * success_score)
        suggestions = []
        for candidate in candidates:
            similarity_score = candidate.get("score", 0.0)
            metadata = candidate.get("metadata", {})
            success_score = float(metadata.get("success_score", 0.5))
            usage_count = int(metadata.get("usage_count", 0))

            # Combined ranking score
            combined_score = similarity_score * 0.7 + success_score * 0.3

            if combined_score >= min_score:
                suggestions.append({
                    "id": candidate.get("id"),
                    "text": candidate.get("text", "")[:500],  # Truncate for display
                    "similarity_score": similarity_score,
                    "success_score": success_score,
                    "usage_count": usage_count,
                    "combined_score": combined_score,
                    "metadata": metadata,
                })

        # Sort by combined score
        suggestions.sort(key=lambda x: x["combined_score"], reverse=True)
        suggestions = suggestions[:top_k]

        await self.log_event("info", f"Generated {len(suggestions)} template suggestions")

        return {
            "action": "suggest_templates",
            "query": query,
            "suggestions": suggestions,
            "count": len(suggestions),
            "backend": "chromadb",
        }

    async def _increment_usage(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Increment usage count for a pattern."""
        pattern_id = input_data.get("pattern_id") or input_data.get("id")
        if not pattern_id:
            raise ValueError("Usage tracking requires 'pattern_id' or 'id' field")

        # Get current document
        doc = await self.store.get_document(pattern_id)
        if not doc:
            raise ValueError(f"Pattern {pattern_id} not found")

        # Increment usage count
        metadata = doc.get("metadata", {})
        usage_count = int(metadata.get("usage_count", 0)) + 1
        metadata["usage_count"] = str(usage_count)

        # Update document
        await self.store.upsert_document(pattern_id, doc["text"], metadata)

        await self.log_event("info", f"Incremented usage count for {pattern_id} to {usage_count}")

        return {
            "action": "increment_usage",
            "pattern_id": pattern_id,
            "usage_count": usage_count,
        }
