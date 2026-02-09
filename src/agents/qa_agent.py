"""QA Agent - Creates comprehensive QA strategy and test plans."""
from __future__ import annotations


import json
from typing import Any, Dict

from .base import BaseAgent, AgentTask, AgentResult


class QAAgent(BaseAgent):
    """Agent specialized in quality assurance and testing strategy."""

    def get_agent_id(self) -> str:
        """Return unique agent identifier."""
        return "qa_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        """Define agent capabilities."""
        return {
            "can_create_test_plans": True,
            "can_define_test_cases": True,
            "can_assess_coverage": True,
            "can_create_qa_strategy": True,
            "output_formats": ["json", "markdown"],
        }

    async def execute(self, task: AgentTask) -> AgentResult:
        """
        Generate QA strategy and test plans from development plan.

        Args:
            task: Task definition

        Returns:
            Agent result with QA artifact
        """
        try:
            self._set_active_task_id(task.task_id)
            await self.log_event("info", "Starting QA strategy generation")

            development_content = task.input_data.get("development") or ""
            architecture_content = task.input_data.get("architecture") or ""
            prd_content = task.input_data.get("prd") or ""
            requirements = (task.input_data.get("requirements") or "").strip()

            if not development_content.strip():
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.agent_id,
                    success=False,
                    output={},
                    artifacts=[],
                    error="Missing development content for QA planning",
                )

            # Build comprehensive system prompt
            system_prompt = self._build_qa_system_prompt()

            # Generate QA strategy (real LLM or mock)
            user_prompt = self._build_qa_user_prompt(
                development_content, architecture_content, prd_content, requirements
            )

            from ..config import settings

            if settings.llm_mode == "mock":
                qa_payload = {
                    "qa_strategy": {
                        "approach": "risk-based testing",
                        "test_levels": ["unit", "integration", "system", "acceptance"],
                        "coverage_target": "85%",
                        "automation_ratio": "70%",
                    },
                    "test_plans": [
                        {
                            "plan_id": "TP-001",
                            "name": "Unit Testing Plan",
                            "objective": "Verify individual components work correctly in isolation",
                            "scope": "All business logic, models, services, and utilities",
                            "test_types": ["unit"],
                            "tools": ["pytest", "jest", "junit"],
                            "coverage_target": "90%",
                            "priority": "high",
                        },
                        {
                            "plan_id": "TP-002",
                            "name": "Integration Testing Plan",
                            "objective": "Verify components work together correctly",
                            "scope": "API endpoints, database interactions, external service integrations",
                            "test_types": ["integration"],
                            "tools": ["pytest-asyncio", "testcontainers", "supertest"],
                            "coverage_target": "80%",
                            "priority": "high",
                        },
                        {
                            "plan_id": "TP-003",
                            "name": "E2E Testing Plan",
                            "objective": "Verify complete user workflows function correctly",
                            "scope": "Critical user journeys and business flows",
                            "test_types": ["e2e"],
                            "tools": ["playwright", "cypress"],
                            "coverage_target": "critical paths only",
                            "priority": "medium",
                        },
                        {
                            "plan_id": "TP-004",
                            "name": "Performance Testing Plan",
                            "objective": "Verify system meets performance requirements",
                            "scope": "API response times, database queries, frontend rendering",
                            "test_types": ["performance"],
                            "tools": ["locust", "k6", "lighthouse"],
                            "coverage_target": "key endpoints and pages",
                            "priority": "medium",
                        },
                    ],
                    "test_cases": [
                        {
                            "case_id": "TC-001",
                            "plan_id": "TP-001",
                            "title": "User model validation",
                            "description": "Verify user model enforces all business rules",
                            "preconditions": ["Database initialized"],
                            "steps": [
                                "Create user with valid data",
                                "Verify user is created",
                                "Attempt to create user with invalid email",
                                "Verify validation error is raised",
                            ],
                            "expected_result": "Valid users created, invalid users rejected with appropriate errors",
                            "priority": "high",
                            "test_type": "unit",
                        },
                        {
                            "case_id": "TC-002",
                            "plan_id": "TP-002",
                            "title": "User registration API",
                            "description": "Verify user registration endpoint works end-to-end",
                            "preconditions": ["API server running", "Database accessible"],
                            "steps": [
                                "POST to /api/users/register with valid data",
                                "Verify 201 status code",
                                "Verify user exists in database",
                                "Verify confirmation email sent",
                            ],
                            "expected_result": "User created, stored in DB, confirmation email sent",
                            "priority": "high",
                            "test_type": "integration",
                        },
                        {
                            "case_id": "TC-003",
                            "plan_id": "TP-003",
                            "title": "Complete user registration flow",
                            "description": "User can register, confirm email, and login",
                            "preconditions": ["Application fully deployed"],
                            "steps": [
                                "Navigate to registration page",
                                "Fill registration form",
                                "Submit form",
                                "Check email for confirmation link",
                                "Click confirmation link",
                                "Login with credentials",
                                "Verify dashboard loads",
                            ],
                            "expected_result": "User successfully registers, confirms, and logs in",
                            "priority": "high",
                            "test_type": "e2e",
                        },
                    ],
                    "coverage_strategy": {
                        "code_coverage": {
                            "target": "85%",
                            "minimum": "75%",
                            "measurement": "line and branch coverage",
                            "tools": ["pytest-cov", "coverage.py", "istanbul"],
                        },
                        "functional_coverage": {
                            "requirements_traceability": "All requirements must have test cases",
                            "risk_coverage": "High and medium risk areas must be fully tested",
                            "user_scenarios": "All critical user paths tested",
                        },
                        "regression_coverage": {
                            "strategy": "Automated regression suite for all releases",
                            "scope": "All existing functionality",
                            "frequency": "every commit via CI/CD",
                        },
                    },
                    "test_environment": {
                        "environments": [
                            {
                                "name": "dev",
                                "purpose": "Developer testing",
                                "data": "synthetic test data",
                                "automation": "unit and integration tests",
                            },
                            {
                                "name": "staging",
                                "purpose": "Pre-production testing",
                                "data": "anonymized production-like data",
                                "automation": "full test suite",
                            },
                            {
                                "name": "production",
                                "purpose": "Smoke tests only",
                                "data": "real data",
                                "automation": "smoke tests and monitoring",
                            },
                        ],
                        "test_data_strategy": "Fixtures for unit, containers for integration, synthetic for e2e",
                    },
                    "quality_metrics": {
                        "defect_metrics": [
                            "defect density (defects per KLOC)",
                            "defect removal efficiency",
                            "mean time to detect (MTTD)",
                            "mean time to resolve (MTTR)",
                        ],
                        "test_metrics": [
                            "test pass rate",
                            "test execution time",
                            "code coverage %",
                            "automation coverage %",
                        ],
                        "release_criteria": {
                            "code_coverage": ">= 85%",
                            "critical_tests_pass": "100%",
                            "high_priority_tests_pass": ">= 95%",
                            "no_blocker_defects": True,
                            "no_critical_defects": True,
                        },
                    },
                    "automation_strategy": {
                        "framework": "pytest + playwright",
                        "ci_integration": "GitHub Actions / GitLab CI",
                        "test_selection": "smart test selection based on code changes",
                        "parallel_execution": "distribute tests across multiple workers",
                        "reporting": "HTML reports + dashboard integration",
                    },
                    "risk_assessment": [
                        {
                            "risk": "Data loss or corruption",
                            "severity": "critical",
                            "probability": "low",
                            "mitigation": "Comprehensive DB transaction tests, backup validation",
                        },
                        {
                            "risk": "Security vulnerabilities",
                            "severity": "critical",
                            "probability": "medium",
                            "mitigation": "Security-focused test cases, penetration testing, dependency scanning",
                        },
                        {
                            "risk": "Performance degradation",
                            "severity": "high",
                            "probability": "medium",
                            "mitigation": "Load testing, performance benchmarks, monitoring",
                        },
                        {
                            "risk": "Integration failures",
                            "severity": "medium",
                            "probability": "medium",
                            "mitigation": "Contract testing, API integration tests, mock services",
                        },
                    ],
                }
                qa_content = json.dumps(qa_payload, indent=2)
            else:
                response_text = await self.query_llm(
                    prompt=user_prompt,
                    system=system_prompt,
                    thinking_budget=2048,
                    max_tokens=settings.anthropic_max_tokens,
                )

                # Try to parse as JSON, fallback to raw text
                try:
                    qa_payload = json.loads(response_text)
                    qa_content = json.dumps(qa_payload, indent=2)
                except json.JSONDecodeError:
                    qa_payload = {"raw_qa": response_text}
                    qa_content = response_text

            # Save QA artifact
            artifact_id = await self.save_artifact(
                artifact_type="qa",
                content=qa_content,
                metadata={
                    "task_id": task.task_id,
                    "development_length": len(development_content),
                    "architecture_length": len(architecture_content),
                    "requirements_length": len(requirements),
                    "prd_length": len(prd_content),
                    "parseable_json": "raw_qa" not in qa_payload,
                },
            )

            await self.log_event("info", f"QA strategy generated successfully: {artifact_id}")

            # Return result
            result = AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                success=True,
                output={
                    "qa": qa_payload,
                    "artifact_id": artifact_id,
                    "next_stage": "security_review",
                },
                artifacts=[artifact_id],
                metadata={
                    "test_plans_count": len(qa_payload.get("test_plans", [])),
                    "test_cases_count": len(qa_payload.get("test_cases", [])),
                    "parseable_json": "raw_qa" not in qa_payload,
                },
            )

            await self.notify_completion(result)
            return result

        except Exception as e:
            await self.log_event(
                "error",
                f"QA strategy generation failed: {type(e).__name__}: {str(e) or repr(e)}",
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

    def _build_qa_system_prompt(self) -> str:
        """Build system prompt for QA strategy generation."""
        guardrails = self._truth_system_guardrails()
        # NOTE: Do not use an f-string here. The prompt intentionally embeds JSON examples
        # containing many `{`/`}` which can trigger `SyntaxError: f-string: expressions nested too deeply`.
        return guardrails + """
You are an expert QA Engineer and Test Architect with deep expertise in software quality assurance.

Your role is to create comprehensive QA strategies, test plans, and test cases based on development plans and system architecture.

## Your Expertise:
- Deep understanding of testing methodologies (unit, integration, system, acceptance, exploratory)
- Experience with test automation frameworks and tools
- Knowledge of test design techniques (boundary value, equivalence partitioning, decision tables)
- Expertise in risk-based testing and test coverage analysis
- Understanding of CI/CD integration and continuous testing
- Knowledge of performance, security, and accessibility testing

## QA Output (JSON format):
{
  "qa_strategy": {
    "approach": "risk-based|test-driven|behavior-driven",
    "test_levels": ["unit", "integration", "system", "acceptance"],
    "coverage_target": "percentage or criteria",
    "automation_ratio": "percentage"
  },
  "test_plans": [
    {
      "plan_id": "TP-XXX",
      "name": "Plan name",
      "objective": "What this plan aims to achieve",
      "scope": "What is covered",
      "test_types": ["unit", "integration", "e2e"],
      "tools": ["testing tools"],
      "coverage_target": "coverage goal",
      "priority": "high|medium|low"
    }
  ],
  "test_cases": [
    {
      "case_id": "TC-XXX",
      "plan_id": "TP-XXX",
      "title": "Test case title",
      "description": "What is being tested",
      "preconditions": ["setup requirements"],
      "steps": ["step-by-step instructions"],
      "expected_result": "Expected outcome",
      "priority": "high|medium|low",
      "test_type": "unit|integration|e2e|performance"
    }
  ],
  "coverage_strategy": {
    "code_coverage": {
      "target": "percentage",
      "minimum": "minimum percentage",
      "measurement": "line|branch|path coverage",
      "tools": ["coverage tools"]
    },
    "functional_coverage": {
      "requirements_traceability": "strategy",
      "risk_coverage": "strategy",
      "user_scenarios": "strategy"
    },
    "regression_coverage": {
      "strategy": "approach",
      "scope": "what to cover",
      "frequency": "how often"
    }
  },
  "test_environment": {
    "environments": [
      {
        "name": "env name",
        "purpose": "what it's for",
        "data": "test data approach",
        "automation": "what runs here"
      }
    ],
    "test_data_strategy": "approach to test data"
  },
  "quality_metrics": {
    "defect_metrics": ["metrics to track"],
    "test_metrics": ["metrics to track"],
    "release_criteria": {
      "code_coverage": "minimum %",
      "critical_tests_pass": "percentage",
      "no_blocker_defects": true
    }
  },
  "automation_strategy": {
    "framework": "automation framework",
    "ci_integration": "CI/CD integration approach",
    "test_selection": "how tests are selected",
    "parallel_execution": "parallelization strategy",
    "reporting": "reporting approach"
  },
  "risk_assessment": [
    {
      "risk": "risk description",
      "severity": "critical|high|medium|low",
      "probability": "high|medium|low",
      "mitigation": "testing approach to mitigate"
    }
  ]
}

## QA Principles:
- **Test early, test often**: Shift-left testing approach
- **Risk-based testing**: Focus on high-risk areas first
- **Automation**: Automate repetitive tests, manual for exploratory
- **Coverage**: Aim for meaningful coverage, not just metrics
- **Continuous improvement**: Learn from defects and improve

## Guidelines:
- Create comprehensive test plans covering all test levels
- Define specific, actionable test cases with clear expected results
- Establish realistic coverage targets based on risk
- Include performance, security, and accessibility testing where relevant
- Design for automation and CI/CD integration
- Focus on quality metrics that matter"""

    def _build_qa_user_prompt(
        self,
        development_content: str,
        architecture_content: str,
        prd_content: str,
        requirements: str,
    ) -> str:
        """Build user prompt for QA strategy generation."""
        prompt = "Create a comprehensive QA strategy using the sources of truth below.\n\n"

        if requirements:
            prompt += f"User Requirements (source of truth):\n{requirements}\n\n"

        if prd_content.strip():
            prompt += f"PRD (source of truth):\n{prd_content}\n\n"

        prompt += f"""Development plan (derived):

{development_content}
"""

        if architecture_content.strip():
            prompt += f"""

And this architecture:

{architecture_content}
"""

        prompt += """

Please create a detailed QA strategy in JSON format following the structure provided.
Focus on:
- Comprehensive test coverage across all levels
- Risk-based approach prioritizing critical areas
- Realistic and actionable test plans
- Specific test cases with clear steps and expected results
- Automation strategy integrated with CI/CD
- Quality metrics and release criteria

Make it practical and aligned with the development approach."""

        return prompt
