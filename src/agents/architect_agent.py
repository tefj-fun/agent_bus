"""Architect Agent - Creates system architecture from PRD and Plan."""
from __future__ import annotations


import json
from typing import Any, Dict

from .base import BaseAgent, AgentTask, AgentResult


class ArchitectAgent(BaseAgent):
    """Agent specialized in creating system architecture designs."""

    def get_agent_id(self) -> str:
        """Return unique agent identifier."""
        return "architect_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        """Define agent capabilities."""
        return {
            "can_design_architecture": True,
            "can_parse_prd": True,
            "can_parse_plan": True,
            "output_formats": ["json", "markdown"],
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Generate system architecture from PRD and plan.

        Args:
            task: Task definition

        Returns:
            Agent result with architecture artifact
        """
        try:
            await self.log_event("info", "Starting architecture design")

            prd_content = task.input_data.get("prd") or task.input_data.get("prd_content") or ""
            plan_content = task.input_data.get("plan") or ""

            if not prd_content.strip():
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=False,
                    output={},
                    artifacts=[],
                    error="Missing PRD content for architecture design",
                )

            # Build comprehensive system prompt
            system_prompt = self._build_architecture_system_prompt()

            # Generate architecture (real LLM or mock)
            user_prompt = self._build_architecture_user_prompt(prd_content, plan_content)

            from ..config import settings

            if settings.llm_mode == "mock":
                architecture_payload = {
                    "system_overview": {
                        "description": "Mock architecture for CI/testing",
                        "architecture_type": "microservices",
                    },
                    "components": [
                        {
                            "id": "comp_1",
                            "name": "API Gateway",
                            "type": "service",
                            "responsibilities": ["Request routing", "Authentication"],
                            "technology": "FastAPI",
                        },
                        {
                            "id": "comp_2",
                            "name": "Database",
                            "type": "datastore",
                            "responsibilities": ["Data persistence"],
                            "technology": "PostgreSQL",
                        },
                    ],
                    "data_flows": [
                        {"from": "comp_1", "to": "comp_2", "description": "API writes to database"}
                    ],
                    "technology_stack": {
                        "backend": "Python/FastAPI",
                        "database": "PostgreSQL",
                        "cache": "Redis",
                    },
                    "deployment": {"strategy": "containerized", "platform": "docker-compose"},
                }
                architecture_content = json.dumps(architecture_payload, indent=2)
            else:
                response_text = await self.query_llm(
                    prompt=user_prompt,
                    system=system_prompt,
                    thinking_budget=2048,
                    max_tokens=settings.anthropic_max_tokens,
                )

                # Try to parse as JSON, fallback to raw text
                try:
                    architecture_payload = json.loads(response_text)
                    architecture_content = json.dumps(architecture_payload, indent=2)
                except json.JSONDecodeError:
                    architecture_payload = {"raw_architecture": response_text}
                    architecture_content = response_text

            # Save architecture as artifact
            artifact_id = await self.save_artifact(
                artifact_type="architecture",
                content=architecture_content,
                metadata={
                    "task_id": task.task_id,
                    "prd_length": len(prd_content),
                    "plan_length": len(plan_content),
                    "parseable_json": "raw_architecture" not in architecture_payload,
                },
            )

            await self.log_event("info", f"Architecture generated successfully: {artifact_id}")

            # Return result
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "architecture": architecture_payload,
                    "artifact_id": artifact_id,
                    "next_stage": "uiux_design",
                },
                artifacts=[artifact_id],
                metadata={
                    "component_count": len(architecture_payload.get("components", [])),
                    "parseable_json": "raw_architecture" not in architecture_payload,
                },
            )

            await self.notify_completion(result)
            return result

        except Exception as e:
            await self.log_event(
                "error",
                f"Architecture generation failed: {type(e).__name__}: {str(e) or repr(e)}",
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

    def _build_architecture_system_prompt(self) -> str:
        """Build system prompt for architecture generation."""
        return """You are an expert Solution Architect specialized in designing scalable, maintainable software systems.

Your role is to transform PRDs and project plans into detailed technical architecture specifications.

## Your Expertise:
- Deep understanding of software architecture patterns (microservices, event-driven, serverless, etc.)
- Experience with system design, component decomposition, and data modeling
- Knowledge of technology stacks, deployment strategies, and scalability considerations
- Ability to identify technical risks and propose mitigation strategies

## Architecture Output (JSON format):
{
  "system_overview": {
    "description": "High-level system description",
    "architecture_type": "microservices|monolith|event-driven|etc"
  },
  "components": [
    {
      "id": "comp_id",
      "name": "Component Name",
      "type": "service|database|queue|cache|etc",
      "responsibilities": ["What this component does"],
      "technology": "Recommended tech stack",
      "interfaces": ["APIs or contracts it exposes"]
    }
  ],
  "data_flows": [
    {
      "from": "component_id",
      "to": "component_id",
      "description": "What data flows and why",
      "protocol": "HTTP|gRPC|async|etc"
    }
  ],
  "data_models": [
    {
      "entity": "Entity name",
      "attributes": ["field1", "field2"],
      "relationships": ["related entities"]
    }
  ],
  "technology_stack": {
    "backend": "Language/Framework",
    "frontend": "Framework",
    "database": "Database system",
    "cache": "Caching solution",
    "message_queue": "Queue system if needed"
  },
  "deployment": {
    "strategy": "containerized|serverless|traditional",
    "platform": "docker|k8s|aws-lambda|etc",
    "scaling": "horizontal|vertical|auto"
  },
  "security": {
    "authentication": "method",
    "authorization": "RBAC|ABAC|etc",
    "data_encryption": "at-rest and in-transit"
  },
  "monitoring": {
    "logging": "solution",
    "metrics": "solution",
    "alerting": "solution"
  }
}

## Guidelines:
- Be specific about technologies and patterns
- Consider scalability, maintainability, and security from the start
- Identify integration points and external dependencies
- Document key architectural decisions and trade-offs
- Keep it practical and implementable"""

    def _build_architecture_user_prompt(self, prd_content: str, plan_content: str) -> str:
        """Build user prompt for architecture generation."""
        prompt = f"""Design a comprehensive system architecture based on this PRD:

{prd_content}
"""

        if plan_content.strip():
            prompt += f"""

And this project plan:

{plan_content}
"""

        prompt += """

Please create a detailed technical architecture specification in JSON format following the structure provided. 
Focus on creating a practical, implementable architecture that addresses the requirements while maintaining 
good engineering practices."""

        return prompt
