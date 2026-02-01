"""UIUX Agent - Creates UI/UX design system from architecture."""

import json
from typing import Any, Dict

from .base import BaseAgent, AgentTask, AgentResult


class UIUXAgent(BaseAgent):
    """Agent specialized in creating UI/UX design systems."""

    def get_agent_id(self) -> str:
        """Return unique agent identifier."""
        return "uiux_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        """Define agent capabilities."""
        return {
            "can_design_uiux": True,
            "can_parse_architecture": True,
            "can_create_design_system": True,
            "output_formats": ["json", "markdown"]
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Generate UI/UX design system from architecture.

        Args:
            task: Task definition

        Returns:
            Agent result with UI/UX artifact
        """
        try:
            await self.log_event("info", "Starting UI/UX design")

            architecture_content = task.input_data.get("architecture") or ""
            prd_content = task.input_data.get("prd") or ""

            if not architecture_content.strip():
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=False,
                    output={},
                    artifacts=[],
                    error="Missing architecture content for UI/UX design",
                )

            # Build comprehensive system prompt
            system_prompt = self._build_uiux_system_prompt()

            # Generate UI/UX design (real LLM or mock)
            user_prompt = self._build_uiux_user_prompt(architecture_content, prd_content)

            from ..config import settings
            if settings.llm_mode == 'mock':
                uiux_payload = {
                    "design_system": {
                        "name": "Mock Design System",
                        "version": "1.0.0",
                        "description": "Mock design system for CI/testing"
                    },
                    "color_palette": {
                        "primary": "#0066CC",
                        "secondary": "#6C757D",
                        "success": "#28A745",
                        "danger": "#DC3545",
                        "neutral": {
                            "100": "#F8F9FA",
                            "900": "#212529"
                        }
                    },
                    "typography": {
                        "font_family": {
                            "primary": "Inter, sans-serif",
                            "monospace": "Fira Code, monospace"
                        },
                        "scale": {
                            "h1": "2rem",
                            "h2": "1.5rem",
                            "body": "1rem",
                            "small": "0.875rem"
                        }
                    },
                    "spacing": {
                        "unit": "8px",
                        "scale": ["4px", "8px", "16px", "24px", "32px", "48px"]
                    },
                    "components": [
                        {
                            "name": "Button",
                            "variants": ["primary", "secondary", "outline"],
                            "states": ["default", "hover", "active", "disabled"]
                        },
                        {
                            "name": "Input",
                            "variants": ["text", "email", "password"],
                            "states": ["default", "focus", "error", "disabled"]
                        },
                        {
                            "name": "Card",
                            "variants": ["default", "elevated"],
                            "states": ["default", "hover"]
                        }
                    ],
                    "layouts": [
                        {
                            "name": "Dashboard",
                            "structure": "header + sidebar + main content + footer",
                            "breakpoints": ["mobile", "tablet", "desktop"]
                        }
                    ],
                    "user_flows": [
                        {
                            "name": "User Login",
                            "steps": ["Landing", "Login Form", "Dashboard"],
                            "interactions": ["click", "type", "submit"]
                        }
                    ],
                    "accessibility": {
                        "wcag_level": "AA",
                        "features": ["keyboard navigation", "screen reader support", "color contrast"]
                    }
                }
                uiux_content = json.dumps(uiux_payload, indent=2)
            else:
                response_text = await self.query_llm(
                    prompt=user_prompt,
                    system=system_prompt,
                    thinking_budget=2048,
                    max_tokens=8192
                )
                
                # Try to parse as JSON, fallback to raw text
                try:
                    uiux_payload = json.loads(response_text)
                    uiux_content = json.dumps(uiux_payload, indent=2)
                except json.JSONDecodeError:
                    uiux_payload = {"raw_design": response_text}
                    uiux_content = response_text

            # Save UI/UX design as artifact
            artifact_id = await self.save_artifact(
                artifact_type="ui_ux",
                content=uiux_content,
                metadata={
                    "task_id": task.task_id,
                    "architecture_length": len(architecture_content),
                    "prd_length": len(prd_content),
                    "parseable_json": "raw_design" not in uiux_payload,
                }
            )

            await self.log_event("info", f"UI/UX design generated successfully: {artifact_id}")

            # Return result
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "ui_ux": uiux_payload,
                    "artifact_id": artifact_id,
                    "next_stage": "development",
                },
                artifacts=[artifact_id],
                metadata={
                    "component_count": len(uiux_payload.get("components", [])),
                    "parseable_json": "raw_design" not in uiux_payload,
                }
            )

            await self.notify_completion(result)
            return result

        except Exception as e:
            await self.log_event(
                "error",
                f"UI/UX design generation failed: {type(e).__name__}: {str(e) or repr(e)}",
            )

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

    def _build_uiux_system_prompt(self) -> str:
        """Build system prompt for UI/UX design generation."""
        return """You are an expert UI/UX Designer specialized in creating comprehensive design systems and user experiences.

Your role is to transform technical architectures into beautiful, usable, and accessible user interfaces.

## Your Expertise:
- Deep understanding of design principles (hierarchy, contrast, balance, consistency)
- Experience with design systems, component libraries, and style guides
- Knowledge of modern UI frameworks (React, Vue, Angular) and design tools (Figma, Sketch)
- Expertise in accessibility (WCAG), responsive design, and mobile-first approaches
- Understanding of user psychology, interaction patterns, and usability heuristics

## UI/UX Design Output (JSON format):
{
  "design_system": {
    "name": "Design system name",
    "version": "1.0.0",
    "description": "Brief description"
  },
  "color_palette": {
    "primary": "#hex",
    "secondary": "#hex",
    "success": "#hex",
    "warning": "#hex",
    "danger": "#hex",
    "neutral": {
      "100": "#lightest",
      "900": "#darkest"
    }
  },
  "typography": {
    "font_family": {
      "primary": "Font stack for body text",
      "heading": "Font stack for headings",
      "monospace": "Font stack for code"
    },
    "scale": {
      "h1": "size",
      "h2": "size",
      "body": "size",
      "small": "size"
    },
    "line_height": {
      "tight": "1.2",
      "normal": "1.5",
      "relaxed": "1.75"
    }
  },
  "spacing": {
    "unit": "Base unit (e.g., 8px)",
    "scale": ["List of spacing values"]
  },
  "breakpoints": {
    "mobile": "320px",
    "tablet": "768px",
    "desktop": "1024px",
    "wide": "1440px"
  },
  "components": [
    {
      "name": "Component name",
      "description": "What it does",
      "variants": ["variant1", "variant2"],
      "states": ["default", "hover", "active", "disabled"],
      "props": ["List of configurable properties"]
    }
  ],
  "layouts": [
    {
      "name": "Layout name",
      "structure": "Description of layout structure",
      "use_cases": ["When to use this layout"],
      "breakpoints": ["How it adapts across devices"]
    }
  ],
  "user_flows": [
    {
      "name": "Flow name",
      "steps": ["Step 1", "Step 2"],
      "screens": ["Screen A", "Screen B"],
      "interactions": ["click", "swipe", "type"]
    }
  ],
  "accessibility": {
    "wcag_level": "A|AA|AAA",
    "features": ["keyboard navigation", "screen reader support", "color contrast"],
    "aria_patterns": ["List of ARIA patterns used"]
  },
  "animations": {
    "timing": "ease-in-out",
    "duration": "200ms",
    "motion_principles": ["Subtle", "Purposeful", "Natural"]
  }
}

## Guidelines:
- Create a cohesive, scalable design system
- Ensure accessibility is built-in, not bolted on
- Design mobile-first, then scale up
- Use clear naming conventions and documentation
- Consider performance (e.g., icon systems, image optimization)
- Provide clear component hierarchy and composition patterns
- Document interaction patterns and micro-interactions"""

    def _build_uiux_user_prompt(self, architecture_content: str, prd_content: str) -> str:
        """Build user prompt for UI/UX design generation."""
        prompt = f"""Design a comprehensive UI/UX system based on this architecture:

{architecture_content}
"""
        
        if prd_content.strip():
            prompt += f"""

And this PRD (for context):

{prd_content}
"""

        prompt += """

Please create a detailed UI/UX design system in JSON format following the structure provided.
Focus on:
- Visual consistency and hierarchy
- Accessible, inclusive design
- Responsive layouts for all devices
- Clear user flows and interactions
- Reusable component library
- Performance-conscious design decisions

Make it beautiful, usable, and implementable."""

        return prompt
