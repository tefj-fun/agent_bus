"""Project Manager Agent - Tracks timelines and delivery plans."""
from __future__ import annotations


import json
from typing import Any, Dict

from .base import BaseAgent, AgentResult, AgentTask
from ..config import settings


class ProjectManager(BaseAgent):
    """Agent specialized in project planning and tracking."""

    def get_agent_id(self) -> str:
        return "project_manager"

    def define_capabilities(self) -> Dict[str, Any]:
        return {
            "can_build_timeline": True,
            "can_define_milestones": True,
            "can_identify_dependencies": True,
            "supports_markdown": True,
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """Generate project plans, timelines, and risk tracking."""
        try:
            await self.log_event("info", "Starting project management planning")

            input_payload = json.dumps(task.input_data or {}, indent=2, sort_keys=True)
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(input_payload)

            plan_content = await self.query_llm(
                prompt=user_prompt,
                system=system_prompt,
                thinking_budget=1536,
                max_tokens=settings.anthropic_max_tokens,
            )

            artifact_id = await self.save_artifact(
                artifact_type="project_plan",
                content=plan_content,
                metadata={
                    "task_id": task.task_id,
                    "input_bytes": len(input_payload.encode("utf-8")),
                    "output_bytes": len(plan_content.encode("utf-8")),
                },
            )

            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "project_plan": plan_content,
                    "artifact_id": artifact_id,
                    "next_stage": "pm_review",
                },
                artifacts=[artifact_id],
                metadata={"sections": self._count_sections(plan_content)},
            )

            await self.notify_completion(result)
            return result

        except Exception as exc:
            await self.log_event("error", f"Project planning failed: {exc}")
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
            "You are a Project Manager. Build delivery timelines, milestones, "
            "dependencies, and risk tracking for the project."
        )

    def _build_user_prompt(self, input_payload: str) -> str:
        return (
            "Create a project plan from the following project context. "
            "Include milestones, timeline estimates, owners, dependencies, "
            "and risks with mitigations.\n\n"
            f"Project context:\n{input_payload}"
        )

    def _count_sections(self, content: str) -> int:
        return sum(1 for line in content.split("\n") if line.strip().startswith("#"))
