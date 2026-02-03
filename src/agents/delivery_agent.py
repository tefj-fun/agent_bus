"""Delivery Agent - packages and delivers final project artifacts."""
from __future__ import annotations


from .base import BaseAgent, AgentContext, AgentTask, AgentResult


class DeliveryAgent(BaseAgent):
    """Delivery agent for final packaging and handoff."""

    def __init__(self, context: AgentContext):
        super().__init__(context=context)

    def get_agent_id(self) -> str:
        return "delivery_agent"

    def define_capabilities(self) -> dict:
        return {
            "name": "Delivery Agent",
            "description": "Packages and delivers final project artifacts",
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Package all artifacts and prepare final delivery.

        Args:
            task: Task containing all prior stage outputs

        Returns:
            TaskResult with delivery package details
        """
        print(f"[{self.agent_id}] INFO: Starting delivery packaging")

        try:
            inputs = task.input_data
            pm_review = inputs.get("pm_review", "")
            all_artifacts = inputs.get("all_artifacts", {})

            # Build delivery summary
            delivery_summary = self._build_delivery_summary(pm_review, all_artifacts)

            # Store artifact
            artifact_id = await self.save_artifact(
                artifact_type="delivery",
                content=delivery_summary,
                metadata={"task_id": task.task_id},
            )

            print(
                f"[{self.agent_id}] INFO: Delivery package created successfully: {artifact_id}"
            )

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "delivery_summary": delivery_summary,
                    "artifact_id": artifact_id,
                    "next_stage": "completed",
                },
                artifacts=[artifact_id],
            )

        except Exception as e:
            print(f"[{self.agent_id}] ERROR: {e}")
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                output={},
                artifacts=[],
                error=str(e),
            )

    def _build_delivery_summary(self, pm_review: str, all_artifacts: dict) -> str:
        """Build final delivery summary document."""
        summary_parts = ["# Project Delivery Package\n"]
        summary_parts.append("## Executive Summary\n")
        summary_parts.append(f"Project completed successfully.\n\n")

        summary_parts.append("## Deliverables\n")
        for artifact_type, content in all_artifacts.items():
            if content:
                summary_parts.append(f"### {artifact_type.replace('_', ' ').title()}\n")
                summary_parts.append(f"✅ Completed\n\n")

        summary_parts.append("## Product Manager Review\n")
        summary_parts.append(pm_review or "_No PM review available._")
        summary_parts.append("\n\n")

        summary_parts.append("## Next Steps\n")
        summary_parts.append("- Review all artifacts\n")
        summary_parts.append("- Deploy to staging environment\n")
        summary_parts.append("- Schedule stakeholder demo\n")

        return "".join(summary_parts)
