"""PRD Agent - Creates Product Requirements Documents."""

import uuid
from typing import Dict, Any, List
from .base import BaseAgent, AgentTask, AgentResult
from ..memory import MemoryStore


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
            await self.log_event("info", "Starting PRD generation")

            sales_requirements = task.input_data.get("requirements", "")

            memory_store = MemoryStore(db_pool=self.context.db_pool, pattern_type_default="prd")
            similar_prds = await self._query_similar_prds(memory_store, sales_requirements)
            memory_hits = [
                {"id": item.get("id"), "score": item.get("score")}
                for item in similar_prds
                if item.get("id") is not None
            ]

            # Build comprehensive system prompt
            system_prompt = self._build_prd_system_prompt()

            # Generate PRD (real LLM or mock)
            user_prompt = self._build_prd_user_prompt(sales_requirements, similar_prds)

            from ..config import settings

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
                    prompt=user_prompt, system=system_prompt, thinking_budget=2048, max_tokens=8192
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
                },
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
- Include examples where helpful"""

    def _build_prd_user_prompt(self, requirements: str, similar_prds: List[Dict[str, Any]]) -> str:
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

        return f"""Generate a comprehensive Product Requirements Document based on these sales requirements:

{requirements}
{memory_context}

Please create a detailed PRD following the structure and guidelines provided. Be thorough but concise, ensuring all requirements are clearly specified and actionable for the engineering team."""

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
