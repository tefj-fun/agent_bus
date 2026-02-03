"""Product Manager Agent - Reviews outputs and makes product decisions."""
from __future__ import annotations


import json
from typing import Any, Dict

from .base import BaseAgent, AgentResult, AgentTask
from ..config import settings


class ProductManager(BaseAgent):
    """Agent specialized in product review and decision making."""

    def get_agent_id(self) -> str:
        return "product_manager"

    def define_capabilities(self) -> Dict[str, Any]:
        return {
            "can_review_outputs": True,
            "can_define_mvp": True,
            "can_prioritize_backlog": True,
            "supports_markdown": True,
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """Review outputs and provide product decisions."""
        try:
            await self.log_event("info", "Starting product management review")

            input_payload = json.dumps(task.input_data or {}, indent=2, sort_keys=True)
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(input_payload)

            review_content = await self.query_llm(
                prompt=user_prompt,
                system=system_prompt,
                thinking_budget=1536,
                max_tokens=settings.anthropic_max_tokens,
            )

            artifact_id = await self.save_artifact(
                artifact_type="pm_review",
                content=review_content,
                metadata={
                    "task_id": task.task_id,
                    "input_bytes": len(input_payload.encode("utf-8")),
                    "output_bytes": len(review_content.encode("utf-8")),
                },
            )

            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "pm_review": review_content,
                    "artifact_id": artifact_id,
                    "next_stage": "delivery",
                },
                artifacts=[artifact_id],
                metadata={"sections": self._count_sections(review_content)},
            )

            await self.notify_completion(result)
            return result

        except Exception as exc:
            await self.log_event("error", f"PM review failed: {exc}")
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

    def _build_system_prompt(self) -> str:
        return (
            "You are a Product Manager reviewing project outputs. "
            "Summarize key decisions, validate scope, identify gaps, and "
            "prioritize MVP and follow-on releases."
        )

    def _build_user_prompt(self, input_payload: str) -> str:
        return (
            "Review the following project outputs and provide a PM summary. "
            "Include MVP scope, prioritized backlog, risks, and decisions needed.\n\n"
            f"Project context:\n{input_payload}"
        )

    def _count_sections(self, content: str) -> int:
        return sum(1 for line in content.split("\n") if line.strip().startswith("#"))
