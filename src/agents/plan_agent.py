"""Plan Agent - Generates project plans from PRDs."""

import json
from typing import Any, Dict, Optional

from .base import BaseAgent, AgentTask, AgentResult


class PlanAgent(BaseAgent):
    """Agent specialized in creating execution plans from PRDs."""

    def get_agent_id(self) -> str:
        """Return unique agent identifier."""
        return "plan_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        """Define agent capabilities."""
        return {
            "can_generate_plan": True,
            "can_parse_prd": True,
            "output_formats": ["json"]
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Generate milestones/tasks/dependencies plan from PRD content.

        Args:
            task: Task definition

        Returns:
            Agent result with plan JSON
        """
        prd_content = task.input_data.get("prd") or task.input_data.get("prd_content") or ""
        if not prd_content.strip():
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                output={},
                artifacts=[],
                error="Missing PRD content for plan generation",
            )

        system_prompt = (
            "You are a senior delivery manager. Produce an implementation plan from a PRD.\n"
            "Return ONLY valid JSON with this shape:\n"
            "{\n"
            '  "milestones": [\n'
            "    {\n"
            '      "id": "ms_1",\n'
            '      "name": "Short title",\n'
            '      "description": "What this milestone delivers",\n'
            '      "tasks": ["task_1", "task_2"]\n'
            "    }\n"
            "  ],\n"
            '  "tasks": [\n'
            "    {\n"
            '      "id": "task_1",\n'
            '      "title": "Task title",\n'
            '      "description": "Task details",\n'
            '      "owner": "role/team",\n'
            '      "dependencies": ["task_0"]\n'
            "    }\n"
            "  ],\n"
            '  "assumptions": ["assumption 1"],\n'
            '  "risks": ["risk 1"]\n'
            "}\n"
        )

        user_prompt = (
            "Generate a delivery plan based on this PRD. "
            "Ensure dependencies are explicit and tasks are actionable.\n\n"
            f"{prd_content}"
        )

        response_text = await self.query_llm(
            prompt=user_prompt,
            system=system_prompt,
            thinking_budget=1536,
            max_tokens=4096,
        )

        plan_payload: Dict[str, Any]
        try:
            plan_payload = json.loads(response_text)
        except json.JSONDecodeError:
            plan_payload = {"raw_plan": response_text}

        plan_text = json.dumps(plan_payload, indent=2)

        artifact_id = await self.save_artifact(
            artifact_type="plan",
            content=plan_text,
            metadata={
                "task_id": task.task_id,
                "parseable_json": "raw_plan" not in plan_payload,
            },
        )

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            output={
                "plan": plan_payload,
                "artifact_id": artifact_id,
            },
            artifacts=[artifact_id],
            metadata={
                "parseable_json": "raw_plan" not in plan_payload,
            },
        )
