"""Technical Writer Agent - Creates user-facing documentation and guides."""

import json
from typing import Any, Dict

from .base import BaseAgent, AgentResult, AgentTask


class TechnicalWriter(BaseAgent):
    """Agent specialized in producing technical documentation."""

    def get_agent_id(self) -> str:
        return "tech_writer"

    def define_capabilities(self) -> Dict[str, Any]:
        return {
            "can_generate_docs": True,
            "doc_types": ["guide", "tutorial", "reference", "release_notes"],
            "supports_markdown": True,
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """Generate technical documentation based on provided inputs."""
        try:
            await self.log_event("info", "Starting technical documentation generation")

            input_payload = json.dumps(task.input_data or {}, indent=2, sort_keys=True)
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(input_payload)

            doc_content = await self.query_llm(
                prompt=user_prompt,
                system=system_prompt,
                thinking_budget=1536,
                max_tokens=4096,
            )

            artifact_id = await self.save_artifact(
                artifact_type="documentation",
                content=doc_content,
                metadata={
                    "task_id": task.task_id,
                    "input_bytes": len(input_payload.encode("utf-8")),
                    "output_bytes": len(doc_content.encode("utf-8")),
                },
            )

            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "documentation": doc_content,
                    "artifact_id": artifact_id,
                    "next_stage": "pm_review",
                },
                artifacts=[artifact_id],
                metadata={"sections": self._count_sections(doc_content)},
            )

            await self.notify_completion(result)
            return result

        except Exception as exc:
            await self.log_event("error", f"Documentation generation failed: {exc}")
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
            "You are an expert Technical Writer. Produce clear, concise, user-facing "
            "documentation. Use headings, bullet lists, and examples where helpful. "
            "Highlight prerequisites, steps, and troubleshooting guidance."
        )

    def _build_user_prompt(self, input_payload: str) -> str:
        return (
            "Create technical documentation based on the following project context. "
            "Include an overview, setup steps, key workflows, and troubleshooting.\n\n"
            f"Project context:\n{input_payload}"
        )

    def _count_sections(self, content: str) -> int:
        return sum(1 for line in content.split("\n") if line.strip().startswith("#"))
