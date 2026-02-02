"""Unit tests for QAAgent."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from src.agents.qa_agent import QAAgent
from src.agents.base import AgentTask, AgentContext


@pytest.fixture
def mock_context():
    """Create a mock agent context."""
    context = MagicMock(spec=AgentContext)
    context.project_id = "test-project"
    context.job_id = "test-job"
    context.session_key = "test-session"
    context.workspace_dir = "/tmp/workspace"
    context.redis_client = AsyncMock()
    context.db_pool = AsyncMock()
    context.anthropic_client = AsyncMock()
    context.skills_manager = MagicMock()
    context.config = {}
    return context


@pytest.fixture
def qa_agent(mock_context):
    """Create a QAAgent instance."""
    return QAAgent(mock_context)


@pytest.mark.asyncio
async def test_qa_agent_initialization(qa_agent):
    """Test QAAgent initialization."""
    assert qa_agent.agent_id == "qa_agent"
    capabilities = qa_agent.capabilities
    assert capabilities["can_create_test_plans"] is True
    assert capabilities["can_define_test_cases"] is True
    assert capabilities["can_assess_coverage"] is True
    assert capabilities["can_create_qa_strategy"] is True


@pytest.mark.asyncio
async def test_qa_agent_execute_mock_mode(qa_agent, mock_context):
    """Test QAAgent execution in mock mode."""
    # Mock the config to enable mock mode
    from src.config import settings

    settings.llm_mode = "mock"

    # Mock the save_artifact method
    qa_agent.save_artifact = AsyncMock(return_value="artifact-qa-123")
    qa_agent.log_event = AsyncMock()
    qa_agent.notify_completion = AsyncMock()

    # Create task
    task = AgentTask(
        task_id="task-1",
        task_type="qa_testing",
        input_data={
            "development": '{"tdd_strategy": "test-first", "code_structure": {}}',
            "architecture": '{"system_overview": "microservices"}',
            "prd": "Test PRD content",
        },
        dependencies=[],
        priority=5,
        metadata={},
    )

    # Execute
    result = await qa_agent.execute(task)

    # Assertions
    assert result.success is True
    assert result.task_id == "task-1"
    assert result.agent_id == "qa_agent"
    assert "qa" in result.output
    assert "artifact_id" in result.output
    assert result.output["artifact_id"] == "artifact-qa-123"
    assert result.output["next_stage"] == "security_review"

    # Verify QA payload structure
    qa = result.output["qa"]
    assert "qa_strategy" in qa
    assert "test_plans" in qa
    assert "test_cases" in qa
    assert "coverage_strategy" in qa
    assert "test_environment" in qa
    assert "quality_metrics" in qa
    assert "automation_strategy" in qa
    assert "risk_assessment" in qa

    # Verify QA strategy
    assert qa["qa_strategy"]["approach"] == "risk-based testing"
    assert "unit" in qa["qa_strategy"]["test_levels"]
    assert "integration" in qa["qa_strategy"]["test_levels"]
    assert qa["qa_strategy"]["coverage_target"] == "85%"

    # Verify test plans
    assert len(qa["test_plans"]) > 0
    plan = qa["test_plans"][0]
    assert "plan_id" in plan
    assert "name" in plan
    assert "objective" in plan
    assert "scope" in plan
    assert "test_types" in plan
    assert "tools" in plan
    assert "coverage_target" in plan
    assert "priority" in plan

    # Verify test cases
    assert len(qa["test_cases"]) > 0
    case = qa["test_cases"][0]
    assert "case_id" in case
    assert "plan_id" in case
    assert "title" in case
    assert "description" in case
    assert "preconditions" in case
    assert "steps" in case
    assert "expected_result" in case
    assert "priority" in case
    assert "test_type" in case

    # Verify coverage strategy
    assert "code_coverage" in qa["coverage_strategy"]
    assert "functional_coverage" in qa["coverage_strategy"]
    assert "regression_coverage" in qa["coverage_strategy"]

    # Verify test environment
    assert "environments" in qa["test_environment"]
    assert len(qa["test_environment"]["environments"]) > 0

    # Verify quality metrics
    assert "defect_metrics" in qa["quality_metrics"]
    assert "test_metrics" in qa["quality_metrics"]
    assert "release_criteria" in qa["quality_metrics"]

    # Verify automation strategy
    assert "framework" in qa["automation_strategy"]
    assert "ci_integration" in qa["automation_strategy"]

    # Verify risk assessment
    assert len(qa["risk_assessment"]) > 0
    risk = qa["risk_assessment"][0]
    assert "risk" in risk
    assert "severity" in risk
    assert "probability" in risk
    assert "mitigation" in risk

    # Verify artifact was saved
    qa_agent.save_artifact.assert_called_once()
    call_args = qa_agent.save_artifact.call_args
    assert call_args[1]["artifact_type"] == "qa"
    assert "qa_strategy" in call_args[1]["content"]


@pytest.mark.asyncio
async def test_qa_agent_missing_development(qa_agent):
    """Test QAAgent with missing development input."""
    qa_agent.log_event = AsyncMock()
    qa_agent.notify_completion = AsyncMock()

    task = AgentTask(
        task_id="task-2",
        task_type="qa_testing",
        input_data={
            "development": "",  # Missing
            "architecture": '{"system": "test"}',
            "prd": "Test PRD",
        },
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await qa_agent.execute(task)

    assert result.success is False
    assert result.error == "Missing development content for QA planning"


@pytest.mark.asyncio
async def test_qa_agent_with_real_llm(qa_agent, mock_context):
    """Test QAAgent with real LLM mode (mocked response)."""
    from src.config import settings

    settings.llm_mode = "real"

    # Mock LLM response
    mock_llm_response = json.dumps(
        {
            "qa_strategy": {
                "approach": "behavior-driven testing",
                "test_levels": ["unit", "integration", "acceptance"],
                "coverage_target": "90%",
                "automation_ratio": "80%",
            },
            "test_plans": [
                {
                    "plan_id": "TP-001",
                    "name": "API Testing Plan",
                    "objective": "Verify API endpoints",
                    "scope": "All REST APIs",
                    "test_types": ["integration"],
                    "tools": ["pytest", "httpx"],
                    "coverage_target": "100%",
                    "priority": "high",
                }
            ],
            "test_cases": [
                {
                    "case_id": "TC-001",
                    "plan_id": "TP-001",
                    "title": "Login API test",
                    "description": "Test login endpoint",
                    "preconditions": ["API running"],
                    "steps": ["POST to /login"],
                    "expected_result": "200 with token",
                    "priority": "high",
                    "test_type": "integration",
                }
            ],
            "coverage_strategy": {
                "code_coverage": {
                    "target": "90%",
                    "minimum": "80%",
                    "measurement": "line coverage",
                    "tools": ["pytest-cov"],
                }
            },
            "test_environment": {
                "environments": [{"name": "test", "purpose": "testing"}],
                "test_data_strategy": "fixtures",
            },
            "quality_metrics": {
                "defect_metrics": ["defect density"],
                "test_metrics": ["pass rate"],
                "release_criteria": {"code_coverage": ">= 90%"},
            },
            "automation_strategy": {"framework": "pytest", "ci_integration": "GitHub Actions"},
            "risk_assessment": [
                {
                    "risk": "API failure",
                    "severity": "high",
                    "probability": "medium",
                    "mitigation": "Comprehensive API tests",
                }
            ],
        }
    )

    qa_agent.query_llm = AsyncMock(return_value=mock_llm_response)
    qa_agent.save_artifact = AsyncMock(return_value="artifact-qa-456")
    qa_agent.log_event = AsyncMock()
    qa_agent.notify_completion = AsyncMock()

    task = AgentTask(
        task_id="task-3",
        task_type="qa_testing",
        input_data={
            "development": '{"tdd_strategy": "test-driven"}',
            "architecture": '{"system": "monolith"}',
            "prd": "Build a web service",
        },
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await qa_agent.execute(task)

    assert result.success is True
    assert result.output["qa"]["qa_strategy"]["approach"] == "behavior-driven testing"
    assert result.output["qa"]["qa_strategy"]["coverage_target"] == "90%"
    assert len(result.output["qa"]["test_plans"]) == 1
    assert result.output["qa"]["test_plans"][0]["name"] == "API Testing Plan"

    # Verify LLM was called
    qa_agent.query_llm.assert_called_once()


@pytest.mark.asyncio
async def test_qa_agent_exception_handling(qa_agent):
    """Test QAAgent exception handling."""
    qa_agent.log_event = AsyncMock()
    qa_agent.notify_completion = AsyncMock()
    qa_agent.save_artifact = AsyncMock(side_effect=Exception("Database error"))

    from src.config import settings

    settings.llm_mode = "mock"

    task = AgentTask(
        task_id="task-4",
        task_type="qa_testing",
        input_data={"development": '{"test": "data"}', "architecture": "", "prd": ""},
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await qa_agent.execute(task)

    assert result.success is False
    assert "Database error" in result.error

    # Verify error was logged
    qa_agent.log_event.assert_called()
    error_calls = [call for call in qa_agent.log_event.call_args_list if call[0][0] == "error"]
    assert len(error_calls) > 0


@pytest.mark.asyncio
async def test_qa_agent_metadata(qa_agent):
    """Test QAAgent metadata tracking."""
    from src.config import settings

    settings.llm_mode = "mock"

    qa_agent.save_artifact = AsyncMock(return_value="artifact-qa-789")
    qa_agent.log_event = AsyncMock()
    qa_agent.notify_completion = AsyncMock()

    task = AgentTask(
        task_id="task-5",
        task_type="qa_testing",
        input_data={
            "development": '{"tdd": "yes"}',
            "architecture": '{"arch": "clean"}',
            "prd": "Product requirements",
        },
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await qa_agent.execute(task)

    assert result.success is True
    assert "test_plans_count" in result.metadata
    assert "test_cases_count" in result.metadata
    assert "parseable_json" in result.metadata
    assert result.metadata["parseable_json"] is True
    assert result.metadata["test_plans_count"] > 0
    assert result.metadata["test_cases_count"] > 0
