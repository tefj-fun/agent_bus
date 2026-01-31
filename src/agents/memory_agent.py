"""Memory Agent - Stores and retrieves project knowledge."""

import json
import uuid
from typing import Any, Dict

from .base import BaseAgent, AgentResult, AgentTask
from ..memory import MemoryStore


class MemoryAgent(BaseAgent):
    """Agent specialized in memory storage and retrieval."""

    def __init__(self, context):
        # initialize store before BaseAgent calls define_capabilities()
        self.store = MemoryStore(db_pool=context.db_pool)
        super().__init__(context)

    def get_agent_id(self) -> str:
        return "memory_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        return {
            "can_store_memory": True,
            "can_query_memory": True,
            "backend": self.store.backend,
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """Store or query memory based on task inputs."""
        try:
            await self.log_event("info", "Starting memory operation")

            action = str(task.input_data.get("action", "query")).lower()
            persist_artifact = task.input_data.get("persist_artifact", True)
            artifact_id = None

            if action in {"store", "upsert", "index"}:
                text = task.input_data.get("text") or task.input_data.get("document")
                if not text:
                    raise ValueError("Memory store requires 'text' or 'document' field")
                doc_id = task.input_data.get("id") or f"mem_{uuid.uuid4().hex[:12]}"
                metadata = task.input_data.get("metadata") or {}
                stored_id = await self.store.upsert_document(doc_id=doc_id, text=text, metadata=metadata)
                output = {
                    "action": "store",
                    "doc_id": stored_id,
                    "backend": self.store.backend,
                }
                if persist_artifact:
                    artifact_id = await self.save_artifact(
                        artifact_type="memory_record",
                        content=text,
                        metadata={"doc_id": stored_id, "metadata": metadata},
                    )

            elif action in {"health", "status"}:
                output = await self.store.health()

            else:
                query = task.input_data.get("query") or task.input_data.get("text")
                if not query:
                    raise ValueError("Memory query requires 'query' or 'text' field")
                top_k = int(task.input_data.get("top_k", 5))
                results = await self.store.query_similar(query=query, top_k=top_k)
                output = {
                    "action": "query",
                    "query": query,
                    "results": results,
                    "backend": self.store.backend,
                }
                if persist_artifact:
                    artifact_id = await self.save_artifact(
                        artifact_type="memory_query",
                        content=json.dumps(output, indent=2),
                        metadata={"top_k": top_k},
                    )

            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output=output,
                artifacts=[artifact_id] if artifact_id else [],
                metadata={"backend": self.store.backend},
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
