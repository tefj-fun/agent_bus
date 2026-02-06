"""Plan Agent - Generates project plans from PRDs."""
from __future__ import annotations


import json
from typing import Any, Dict

from .base import BaseAgent, AgentTask, AgentResult


class PlanAgent(BaseAgent):
    """Agent specialized in creating execution plans from PRDs."""

    def get_agent_id(self) -> str:
        """Return unique agent identifier."""
        return "plan_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        """Define agent capabilities."""
        return {"can_generate_plan": True, "can_parse_prd": True, "output_formats": ["json"]}

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Generate milestones/tasks/dependencies plan from PRD content.

        Args:
            task: Task definition

        Returns:
            Agent result with plan JSON
        """
        self._set_active_task_id(task.task_id)
        requirements = (task.input_data.get("requirements") or "").strip()
        prd_content = task.input_data.get("prd") or task.input_data.get("prd_content") or ""
        feature_tree_content = task.input_data.get("feature_tree") or ""
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
            f"{self._truth_system_guardrails()}\n"
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

        user_prompt = self._build_user_prompt(prd_content, requirements, feature_tree_content)

        # Generate plan (real LLM or mock)
        from ..config import settings

        if settings.llm_mode == "mock":
            plan_payload = {
                "milestones": [
                    {
                        "id": "ms_1",
                        "name": "Mock milestone",
                        "description": "Deterministic plan output for CI/testing",
                        "tasks": ["task_1", "task_2"],
                    }
                ],
                "tasks": [
                    {
                        "id": "task_1",
                        "title": "Mock task 1",
                        "description": "Do the first thing",
                        "owner": "engineering",
                        "dependencies": [],
                    },
                    {
                        "id": "task_2",
                        "title": "Mock task 2",
                        "description": "Do the second thing",
                        "owner": "engineering",
                        "dependencies": ["task_1"],
                    },
                ],
                "assumptions": ["Mock mode: no external LLM calls"],
                "risks": ["Mock plan may diverge from real plan format"],
            }
            response_text = json.dumps(plan_payload)
        else:
            response_text = await self.query_llm(
                prompt=user_prompt,
                system=system_prompt,
                thinking_budget=1536,
                max_tokens=settings.anthropic_max_tokens,
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
                "requirements_length": len(requirements),
                "feature_tree_length": len(feature_tree_content),
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

    def _build_user_prompt(
        self, prd_content: str, requirements: str, feature_tree_content: str
    ) -> str:
        prompt = (
            "Generate a delivery plan based on the sources of truth below. "
            "Ensure dependencies are explicit and tasks are actionable.\n\n"
        )

        if requirements:
            prompt += f"User Requirements (source of truth):\n{requirements}\n\n"

        prompt += f"PRD (source of truth):\n{prd_content}\n\n"

        if feature_tree_content.strip():
            prompt += f"Feature Tree (derived, for structure only):\n{feature_tree_content}\n\n"

        prompt += "Return JSON only."
        return prompt
