"""PRD Agent - Creates Product Requirements Documents."""

from __future__ import annotations

import uuid
from typing import Dict, Any, List, Optional
import hashlib
from .base import BaseAgent, AgentTask, AgentResult
from ..config import settings
from ..memory import MemoryStore, create_memory_store


class PRDAgent(BaseAgent):
    """Agent specialized in creating Product Requirements Documents."""

    def get_agent_id(self) -> str:
        """Return unique agent identifier."""
        return "prd_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        """Define agent capabilities."""
        return {
            "can_parse_requirements": True,
            "can_generate_prd": True,
            "can_validate_specifications": True,
            "can_query_memory": True,
            "output_formats": ["markdown", "json"],
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Generate Product Requirements Document from sales requirements.

        Args:
            task: Task definition

        Returns:
            Agent result with PRD
        """
        try:
            self._set_active_task_id(task.task_id)
            await self.log_event("info", "Starting PRD generation")

            sales_requirements = task.input_data.get("requirements", "")
            change_request_notes = task.input_data.get("change_request_notes") or ""
            change_requested_at = task.input_data.get("change_requested_at") or ""
            previous_prd = task.input_data.get("previous_prd") or ""
            previous_prd_artifact_id = task.input_data.get("previous_prd_artifact_id") or ""

            # If previous PRD not provided, attempt to load latest from DB
            if not previous_prd:
                previous_prd, previous_prd_artifact_id = await self._load_latest_prd()

            prd_version = await self._next_prd_version()
            previous_prd_hash = (
                hashlib.sha256(previous_prd.encode("utf-8")).hexdigest() if previous_prd else None
            )

            memory_store = create_memory_store(
                settings.memory_backend,
                db_pool=self.context.db_pool,
                pattern_type_default="prd",
                collection_name=settings.chroma_collection_name,
                persist_directory=settings.chroma_persist_directory,
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            similar_prds = await self._query_similar_prds(memory_store, sales_requirements)
            memory_hits = [
                {"id": item.get("id"), "score": item.get("score")}
                for item in similar_prds
                if item.get("id") is not None
            ]

            # Build comprehensive system prompt
            system_prompt = self._build_prd_system_prompt()

            # Generate PRD (real LLM or mock)
            user_prompt = self._build_prd_user_prompt(
                sales_requirements=sales_requirements,
                similar_prds=similar_prds,
                previous_prd=previous_prd,
                change_request_notes=change_request_notes,
            )

            if settings.llm_mode == "mock":
                prd_content = (
                    "# Product Requirements Document: Mock PRD\n\n"
                    "## Executive Summary\n"
                    "This is a deterministic mock PRD generated for CI/testing.\n\n"
                    "## Input Requirements\n"
                    f"{sales_requirements}\n\n"
                    "## Functional Requirements\n"
                    "- FR-1: The system shall accept requirement submissions.\n"
                    "- FR-2: The system shall generate and store a PRD artifact.\n"
                    "- FR-3: The system shall support HITL approval.\n\n"
                    "## Non-Functional Requirements\n"
                    "- NFR-1: Deterministic outputs in mock mode.\n"
                )
            else:
                prd_content = await self.query_llm(
                    prompt=user_prompt,
                    system=system_prompt,
                    thinking_budget=2048,
                    max_tokens=settings.prd_max_tokens,
                )

            # Save PRD as artifact
            artifact_id = await self.save_artifact(
                artifact_type="prd",
                content=prd_content,
                metadata={
                    "requirements_length": len(sales_requirements),
                    "prd_length": len(prd_content),
                    "task_id": task.task_id,
                    "memory_hits": memory_hits,
                    "prd_version": prd_version,
                    "previous_prd_artifact_id": previous_prd_artifact_id or None,
                    "previous_prd_hash": previous_prd_hash,
                    "change_request_notes": change_request_notes or None,
                    "change_requested_at": change_requested_at or None,
                },
                artifact_id=f"{self.agent_id}_v{prd_version}_prd_{self.context.job_id}",
            )

            await self.log_event("info", f"PRD generated successfully: {artifact_id}")

            await memory_store.upsert_document(
                doc_id=artifact_id or f"prd_{uuid.uuid4().hex[:12]}",
                text=prd_content,
                metadata={
                    "pattern_type": "prd",
                    "project_id": self.context.project_id,
                    "job_id": self.context.job_id,
                    "stage": "prd_generation",
                    "artifact_id": artifact_id,
                },
            )

            # Return result
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "prd_content": prd_content,
                    "artifact_id": artifact_id,
                    "next_stage": "architecture_design",
                    "memory_hits": memory_hits,
                },
                artifacts=[artifact_id],
                metadata={
                    "word_count": len(prd_content.split()),
                    "sections": self._count_sections(prd_content),
                    "memory_hits": memory_hits,
                },
            )

            await self.notify_completion(result)
            return result

        except Exception as e:
            await self.log_event(
                "error",
                f"PRD generation failed: {type(e).__name__}: {str(e) or repr(e)}",
            )

            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                output={},
                artifacts=[],
                error=str(e),
            )

            await self.notify_completion(result)
            return result

    def _build_prd_system_prompt(self) -> str:
        """Build system prompt for PRD generation."""
        return """You are an expert Product Manager and Technical Writer specialized in creating comprehensive Product Requirements Documents (PRDs).

Your role is to transform sales requirements into detailed, actionable PRDs that engineering teams can use to build software.

## Your Expertise:
- Deep understanding of software product development
- Ability to clarify ambiguous requirements
- Experience with user stories, acceptance criteria, and technical specifications
- Knowledge of industry best practices for PRD documentation

## PRD Structure:
1. **Executive Summary**: Brief overview of the product/feature
2. **Problem Statement**: What problem are we solving?
3. **Goals and Objectives**: Measurable success criteria
4. **User Personas**: Who will use this?
5. **User Stories**: As a [user], I want [feature] so that [benefit]
6. **Functional Requirements**: Detailed feature specifications
7. **Non-Functional Requirements**: Performance, security, scalability
8. **Technical Constraints**: Known limitations or dependencies
9. **Success Metrics**: How will we measure success?
10. **Timeline and Milestones**: High-level project phases

## Guidelines:
- Be specific and actionable
- Include acceptance criteria for each requirement
- Consider edge cases and error scenarios
- Prioritize requirements (Must-have, Should-have, Nice-to-have)
- Use clear, unambiguous language
- Include examples where helpful
- If change requests are provided, revise the prior PRD rather than starting from scratch.
  Preserve correct sections and only modify what the change request requires."""

    def _build_prd_user_prompt(
        self,
        sales_requirements: str,
        similar_prds: List[Dict[str, Any]],
        previous_prd: str = "",
        change_request_notes: str = "",
    ) -> str:
        """Build user prompt for PRD generation."""
        memory_context = ""
        if similar_prds:
            snippets = []
            for item in similar_prds:
                snippet = (item.get("text") or "").strip()
                if snippet:
                    snippets.append(snippet[:800])
            if snippets:
                joined = "\n\n".join(f"- {snippet}" for snippet in snippets)
                memory_context = "\n\nRelevant snippets from prior PRDs:\n" f"{joined}\n"

        change_context = ""
        if change_request_notes:
            change_context = (
                "\n\nChange requests from reviewer:\n"
                f"{change_request_notes}\n"
                "Please address these changes explicitly.\n"
            )

        previous_context = ""
        if previous_prd:
            previous_context = (
                "\n\nPrevious PRD (for reference; revise this document):\n"
                f"{previous_prd}\n"
            )

        return f"""Generate a comprehensive Product Requirements Document based on these sales requirements:

{sales_requirements}
{memory_context}{change_context}{previous_context}

Please create a detailed PRD following the structure and guidelines provided. Be thorough but concise, ensuring all requirements are clearly specified and actionable for the engineering team."""

    async def _load_latest_prd(self) -> tuple[str, str]:
        """Load the latest PRD content and artifact ID from the database."""
        async with self.context.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, content, metadata
                FROM artifacts
                WHERE job_id = $1 AND type = 'prd'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                self.context.job_id,
            )
            if not row:
                return "", ""
            content = row.get("content") or ""
            metadata = row.get("metadata") or {}
            if isinstance(content, str) and content.startswith("[file:") and content.endswith("]"):
                file_path = None
                if isinstance(metadata, dict):
                    file_path = metadata.get("_file_path")
                if file_path:
                    try:
                        with open(file_path, "r") as f:
                            content = f.read()
                    except Exception:
                        pass
            return content, row.get("id") or ""

    async def _next_prd_version(self) -> int:
        """Compute the next PRD version number for this job."""
        async with self.context.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) AS count FROM artifacts WHERE job_id = $1 AND type = 'prd'",
                self.context.job_id,
            )
        count = int(row["count"]) if row and row.get("count") is not None else 0
        return count + 1

    async def _query_similar_prds(
        self,
        memory_store: MemoryStore,
        requirements: str,
    ) -> List[Dict[str, Any]]:
        """Query memory for similar past PRDs."""
        if not requirements.strip():
            return []
        return await memory_store.query_similar(
            query=requirements,
            top_k=3,
            pattern_type="prd",
        )

    def _count_sections(self, prd_content: str) -> int:
        """Count sections in PRD (markdown headers)."""
        lines = prd_content.split("\n")
        return sum(1 for line in lines if line.startswith("#"))
