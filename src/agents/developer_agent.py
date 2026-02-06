"""Developer Agent - Creates code structure from UI/UX design with TDD approach."""
from __future__ import annotations


import json
from typing import Any, Dict

from .base import BaseAgent, AgentTask, AgentResult


class DeveloperAgent(BaseAgent):
    """Agent specialized in software development with TDD methodology."""

    def get_agent_id(self) -> str:
        """Return unique agent identifier."""
        return "developer_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        """Define agent capabilities."""
        return {
            "can_write_code": True,
            "can_parse_architecture": True,
            "can_parse_uiux": True,
            "can_create_tdd_strategy": True,
            "output_formats": ["json", "markdown"],
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Generate code structure with TDD strategy from architecture and UI/UX.

        Args:
            task: Task definition

        Returns:
            Agent result with development artifact
        """
        try:
            self._set_active_task_id(task.task_id)
            await self.log_event("info", "Starting development with TDD approach")

            architecture_content = task.input_data.get("architecture") or ""
            uiux_content = task.input_data.get("ui_ux") or ""
            prd_content = task.input_data.get("prd") or ""
            requirements = (task.input_data.get("requirements") or "").strip()

            if not architecture_content.strip():
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=False,
                    output={},
                    artifacts=[],
                    error="Missing architecture content for development",
                )

            # Build comprehensive system prompt
            system_prompt = self._build_developer_system_prompt()

            # Generate development plan (real LLM or mock)
            user_prompt = self._build_developer_user_prompt(
                architecture_content, uiux_content, prd_content, requirements
            )

            from ..config import settings

            if settings.llm_mode == "mock":
                development_payload = {
                    "tdd_strategy": {
                        "approach": "test-first development",
                        "test_framework": "pytest",
                        "coverage_target": "80%",
                        "test_types": ["unit", "integration", "e2e"],
                    },
                    "development_phases": [
                        {
                            "phase": 1,
                            "name": "Core Models & Business Logic",
                            "description": "Implement data models and core business logic",
                            "tdd_steps": [
                                "Write model tests",
                                "Implement models",
                                "Write business logic tests",
                                "Implement business logic",
                                "Refactor",
                            ],
                        },
                        {
                            "phase": 2,
                            "name": "API Layer",
                            "description": "Build API endpoints and request handlers",
                            "tdd_steps": [
                                "Write API endpoint tests",
                                "Implement endpoints",
                                "Write integration tests",
                                "Refactor",
                            ],
                        },
                        {
                            "phase": 3,
                            "name": "Frontend Components",
                            "description": "Develop UI components and views",
                            "tdd_steps": [
                                "Write component tests",
                                "Implement components",
                                "Write interaction tests",
                                "Refactor",
                            ],
                        },
                    ],
                    "code_structure": {
                        "backend": {
                            "language": "Python",
                            "framework": "FastAPI",
                            "structure": {
                                "src/": {
                                    "models/": ["user.py", "product.py"],
                                    "services/": ["user_service.py", "product_service.py"],
                                    "api/": ["routes.py", "dependencies.py"],
                                    "config.py": "Configuration management",
                                    "main.py": "Application entry point",
                                },
                                "tests/": {
                                    "unit/": ["test_models.py", "test_services.py"],
                                    "integration/": ["test_api.py"],
                                    "conftest.py": "Pytest fixtures",
                                },
                            },
                        },
                        "frontend": {
                            "framework": "React",
                            "structure": {
                                "src/": {
                                    "components/": ["Button.tsx", "Input.tsx", "Card.tsx"],
                                    "pages/": ["Dashboard.tsx", "Login.tsx"],
                                    "services/": ["api.ts"],
                                    "App.tsx": "Main app component",
                                },
                                "tests/": {
                                    "components/": ["Button.test.tsx"],
                                    "integration/": ["user-flow.test.tsx"],
                                },
                            },
                        },
                    },
                    "testing_strategy": {
                        "unit_tests": {
                            "coverage": "All business logic, models, services",
                            "tools": ["pytest", "pytest-cov", "jest"],
                            "mocking": "Use mocks for external dependencies",
                        },
                        "integration_tests": {
                            "coverage": "API endpoints, database interactions",
                            "tools": ["pytest-asyncio", "httpx", "testing-library"],
                            "setup": "Use test database and fixtures",
                        },
                        "e2e_tests": {
                            "coverage": "Critical user flows",
                            "tools": ["playwright", "cypress"],
                            "setup": "Full stack with test data",
                        },
                    },
                    "quality_gates": {
                        "pre_commit": ["linting", "type checking", "fast unit tests"],
                        "ci_pipeline": [
                            "all tests",
                            "coverage report (min 80%)",
                            "security scan",
                            "build verification",
                        ],
                    },
                    "dependencies": {
                        "backend": [
                            "fastapi>=0.104.0",
                            "pydantic>=2.0.0",
                            "sqlalchemy>=2.0.0",
                            "pytest>=7.4.0",
                            "pytest-asyncio>=0.21.0",
                            "pytest-cov>=4.1.0",
                        ],
                        "frontend": [
                            "react>=18.0.0",
                            "typescript>=5.0.0",
                            "jest>=29.0.0",
                            "@testing-library/react>=14.0.0",
                        ],
                    },
                    "development_workflow": {
                        "steps": [
                            "1. Write failing test for new feature",
                            "2. Write minimal code to make test pass",
                            "3. Run all tests to ensure no regression",
                            "4. Refactor code while keeping tests green",
                            "5. Commit with descriptive message",
                            "6. Push and create PR",
                        ],
                        "branch_strategy": "feature branches with PR reviews",
                        "code_review": "Required before merge",
                    },
                }
                development_content = json.dumps(development_payload, indent=2)
            else:
                response_text = await self.query_llm(
                    prompt=user_prompt,
                    system=system_prompt,
                    thinking_budget=2048,
                    max_tokens=settings.anthropic_max_tokens,
                )

                # Try to parse as JSON, fallback to raw text
                try:
                    development_payload = json.loads(response_text)
                    development_content = json.dumps(development_payload, indent=2)
                except json.JSONDecodeError:
                    development_payload = {"raw_development": response_text}
                    development_content = response_text

            # Save development artifact
            artifact_id = await self.save_artifact(
                artifact_type="development",
                content=development_content,
                metadata={
                    "task_id": task.task_id,
                    "architecture_length": len(architecture_content),
                    "uiux_length": len(uiux_content),
                    "requirements_length": len(requirements),
                    "prd_length": len(prd_content),
                    "parseable_json": "raw_development" not in development_payload,
                },
            )

            await self.log_event("info", f"Development plan generated successfully: {artifact_id}")

            # Return result
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "development": development_payload,
                    "artifact_id": artifact_id,
                    "next_stage": "qa_testing",
                },
                artifacts=[artifact_id],
                metadata={
                    "phases_count": len(development_payload.get("development_phases", [])),
                    "parseable_json": "raw_development" not in development_payload,
                },
            )

            await self.notify_completion(result)
            return result

        except Exception as e:
            await self.log_event(
                "error",
                f"Development plan generation failed: {type(e).__name__}: {str(e) or repr(e)}",
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

    def _build_developer_system_prompt(self) -> str:
        """Build system prompt for development plan generation."""
        return f"""{self._truth_system_guardrails()}
You are an expert Software Developer specialized in Test-Driven Development (TDD) and clean code practices.

Your role is to transform architecture and UI/UX designs into implementable code structure with comprehensive TDD strategy.

## Your Expertise:
- Deep understanding of TDD methodology (Red-Green-Refactor cycle)
- Experience with multiple programming languages, frameworks, and testing tools
- Knowledge of software design patterns, SOLID principles, and clean code
- Expertise in test automation, continuous integration, and quality gates
- Understanding of frontend and backend development best practices

## Development Output (JSON format):
{
  "tdd_strategy": {
    "approach": "test-first|test-driven|behavior-driven",
    "test_framework": "pytest|jest|junit|etc",
    "coverage_target": "percentage",
    "test_types": ["unit", "integration", "e2e", "etc"]
  },
  "development_phases": [
    {
      "phase": 1,
      "name": "Phase name",
      "description": "What to build in this phase",
      "tdd_steps": ["Step-by-step TDD approach for this phase"]
    }
  ],
  "code_structure": {
    "backend": {
      "language": "Programming language",
      "framework": "Framework choice",
      "structure": {
        "directory/": {
          "subdirectory/": ["file1.ext", "file2.ext"],
          "file.ext": "File purpose"
        }
      }
    },
    "frontend": {
      "framework": "Framework choice",
      "structure": {
        "directory/": "Structure description"
      }
    }
  },
  "testing_strategy": {
    "unit_tests": {
      "coverage": "What to test",
      "tools": ["testing tools"],
      "mocking": "Mocking strategy"
    },
    "integration_tests": {
      "coverage": "What to test",
      "tools": ["testing tools"],
      "setup": "Test environment setup"
    },
    "e2e_tests": {
      "coverage": "Critical user flows",
      "tools": ["testing tools"],
      "setup": "Full stack setup"
    }
  },
  "quality_gates": {
    "pre_commit": ["checks before commit"],
    "ci_pipeline": ["checks in CI/CD"]
  },
  "dependencies": {
    "backend": ["list of dependencies with versions"],
    "frontend": ["list of dependencies with versions"]
  },
  "development_workflow": {
    "steps": ["Step-by-step development workflow"],
    "branch_strategy": "Git branching strategy",
    "code_review": "Code review process"
  }
}

## TDD Principles:
- **Red**: Write a failing test first
- **Green**: Write minimal code to make the test pass
- **Refactor**: Improve code while keeping tests green
- **Test coverage**: Aim for high coverage, but focus on meaningful tests
- **Test clarity**: Tests should be readable and document behavior
- **Fast feedback**: Tests should run quickly

## Guidelines:
- Create a practical, phased development plan
- Define clear TDD workflow for each phase
- Structure code for testability (dependency injection, single responsibility)
- Include comprehensive testing strategy (unit, integration, e2e)
- Specify quality gates and CI/CD integration
- Provide realistic dependency lists
- Focus on maintainability and code quality"""

    def _build_developer_user_prompt(
        self,
        architecture_content: str,
        uiux_content: str,
        prd_content: str,
        requirements: str,
    ) -> str:
        """Build user prompt for development plan generation."""
        prompt = "Create a comprehensive development plan with TDD strategy using the sources of truth below.\n\n"

        if requirements:
            prompt += f"User Requirements (source of truth):\n{requirements}\n\n"

        if prd_content.strip():
            prompt += f"PRD (source of truth):\n{prd_content}\n\n"

        prompt += f"""Architecture (derived):

{architecture_content}
"""

        if uiux_content.strip():
            prompt += f"""

And this UI/UX design:

{uiux_content}
"""

        prompt += """

Please create a detailed development plan in JSON format following the structure provided.
Focus on:
- Clear TDD methodology (Red-Green-Refactor)
- Phased development approach
- Comprehensive testing strategy
- Realistic code structure and dependencies
- Quality gates and CI/CD integration
- Practical workflow for developers

Make it actionable and implementable with TDD best practices."""

        return prompt
