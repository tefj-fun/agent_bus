"""Architect Agent - Creates system architecture from PRD and Plan."""
from __future__ import annotations


import json
import re
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
            self._set_active_task_id(task.task_id)
            await self.log_event("info", "Starting architecture design")

            requirements = (task.input_data.get("requirements") or "").strip()
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
            user_prompt = self._build_architecture_user_prompt(
                prd_content, requirements, plan_content
            )

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
                    # Architecture should be concise. Very large outputs tend to get truncated,
                    # which breaks downstream JSON parsing and UI renderers.
                    max_tokens=min(settings.anthropic_max_tokens, 6000),
                )

                architecture_payload, architecture_content = await self._coerce_to_architecture_json(
                    response_text=response_text, system_prompt=system_prompt
                )

            # Save architecture as artifact
            artifact_id = await self.save_artifact(
                artifact_type="architecture",
                content=architecture_content,
                metadata={
                    "task_id": task.task_id,
                    "requirements_length": len(requirements),
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
        guardrails = self._truth_system_guardrails()
        # NOTE: Do not use an f-string here. The prompt intentionally embeds JSON examples
        # containing many `{`/`}` which can trigger `SyntaxError: f-string: expressions nested too deeply`.
        return guardrails + """
You are an expert Solution Architect specialized in designing scalable, maintainable software systems.

Your role is to transform PRDs and project plans into detailed technical architecture specifications.

## Your Expertise:
- Deep understanding of software architecture patterns (microservices, event-driven, serverless, etc.)
- Experience with system design, component decomposition, and data modeling
- Knowledge of technology stacks, deployment strategies, and scalability considerations
- Ability to identify technical risks and propose mitigation strategies

## Architecture Output (JSON format):
IMPORTANT:
- Output MUST be a single valid JSON object and NOTHING ELSE (no markdown, no headings, no code fences).
- Keep it concise so it fits comfortably within the output limit.
- Prefer short arrays and small strings over long prose.

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
- Keep it practical and implementable
- Size limits:
  - components: <= 12
  - data_flows: <= 12
  - data_models: <= 10
  - keep any "risks"/"decisions" sections very short if included"""

    def _build_architecture_user_prompt(
        self, prd_content: str, requirements: str, plan_content: str
    ) -> str:
        """Build user prompt for architecture generation."""
        prompt = "Design a comprehensive system architecture using the sources of truth below.\n\n"

        if requirements:
            prompt += f"User Requirements (source of truth):\n{requirements}\n\n"

        prompt += f"PRD (source of truth):\n{prd_content}\n"

        if plan_content.strip():
            prompt += f"""

And this project plan:

{plan_content}
"""

        prompt += """

Please create a technical architecture specification as a SINGLE JSON object following the structure provided.
Return ONLY JSON, no markdown or code fences.

Constraints:
- Keep it implementable and specific.
- Be concise: avoid long narrative paragraphs.
- Respect the size limits from the system prompt (components/flows/models).
"""

        return prompt

    @staticmethod
    def _extract_json_from_code_fence(value: str) -> str | None:
        """
        Best-effort: extract JSON from a markdown code fence.

        Handles both closed fences:
          ```json
          {...}
          ```
        and unclosed fences (take the remainder).
        """
        # Closed fence
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", value, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # Unclosed fence
        m2 = re.search(r"```(?:json)?\s*", value, flags=re.IGNORECASE)
        if m2:
            return value[m2.end() :].strip()

        return None

    async def _coerce_to_architecture_json(
        self, response_text: str, system_prompt: str
    ) -> tuple[Dict[str, Any], str]:
        """
        Convert LLM output into parseable JSON for the architecture artifact.

        The LLM is instructed to output JSON only, but we still harden:
        - Try raw JSON parse
        - Try extracting JSON from code fences
        - As a last resort, ask the LLM to repair into strict JSON
        """
        # 1) Direct JSON
        try:
            payload = json.loads(response_text)
            if isinstance(payload, dict):
                return payload, json.dumps(payload, indent=2)
        except json.JSONDecodeError:
            pass

        # 2) Code-fence extraction
        extracted = self._extract_json_from_code_fence(response_text) or ""
        if extracted:
            try:
                payload = json.loads(extracted)
                if isinstance(payload, dict):
                    return payload, json.dumps(payload, indent=2)
            except json.JSONDecodeError:
                pass

        # 3) Repair: ask for strict JSON only (small output)
        repair_system = (
            system_prompt
            + "\n\nYou will be given an invalid/non-JSON architecture draft. "
            "Your job is to output a single valid JSON object that follows the schema. "
            "Do not include any other text."
        )
        repair_prompt = (
            "Convert the following draft into a single valid JSON object.\n\n"
            "DRAFT (may be truncated/invalid):\n"
            f"{response_text}\n"
        )

        from ..config import settings

        repaired = await self.query_llm(
            prompt=repair_prompt,
            system=repair_system,
            thinking_budget=1024,
            max_tokens=min(settings.anthropic_max_tokens, 4000),
        )
        try:
            payload = json.loads(repaired)
            if isinstance(payload, dict):
                return payload, json.dumps(payload, indent=2)
        except json.JSONDecodeError:
            pass

        # Final fallback: persist raw text so UI can at least show something
        return {"raw_architecture": response_text}, response_text
