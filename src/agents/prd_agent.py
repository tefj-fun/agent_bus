"""PRD Agent - Creates Product Requirements Documents."""

from typing import Dict, Any
from .base import BaseAgent, AgentTask, AgentResult


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
            "output_formats": ["markdown", "json"]
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

            # Query memory for similar past PRDs
            # similar_prds = await self._query_similar_prds(sales_requirements)

            # Build comprehensive system prompt
            system_prompt = self._build_prd_system_prompt()

            # Generate PRD using Claude with extended thinking
            user_prompt = self._build_prd_user_prompt(sales_requirements)

            prd_content = await self.query_llm(
                prompt=user_prompt,
                system=system_prompt,
                thinking_budget=2048,
                max_tokens=8192
            )

            # Save PRD as artifact
            artifact_id = await self.save_artifact(
                artifact_type="prd",
                content=prd_content,
                metadata={
                    "requirements_length": len(sales_requirements),
                    "prd_length": len(prd_content),
                    "task_id": task.task_id
                }
            )

            await self.log_event("info", f"PRD generated successfully: {artifact_id}")

            # Return result
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "prd_content": prd_content,
                    "artifact_id": artifact_id,
                    "next_stage": "architecture_design"
                },
                artifacts=[artifact_id],
                metadata={
                    "word_count": len(prd_content.split()),
                    "sections": self._count_sections(prd_content)
                }
            )

            await self.notify_completion(result)
            return result

        except Exception as e:
            await self.log_event("error", f"PRD generation failed: {str(e)}")

            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=False,
                output={},
                artifacts=[],
                error=str(e)
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

    def _build_prd_user_prompt(self, requirements: str) -> str:
        """Build user prompt for PRD generation."""
        return f"""Generate a comprehensive Product Requirements Document based on these sales requirements:

{requirements}

Please create a detailed PRD following the structure and guidelines provided. Be thorough but concise, ensuring all requirements are clearly specified and actionable for the engineering team."""

    def _count_sections(self, prd_content: str) -> int:
        """Count sections in PRD (markdown headers)."""
        lines = prd_content.split("\n")
        return sum(1 for line in lines if line.startswith("#"))
