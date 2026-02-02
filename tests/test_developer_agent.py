"""Unit tests for DeveloperAgent."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from src.agents.developer_agent import DeveloperAgent
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
def developer_agent(mock_context):
    """Create a DeveloperAgent instance."""
    return DeveloperAgent(mock_context)


@pytest.mark.asyncio
async def test_developer_agent_initialization(developer_agent):
    """Test DeveloperAgent initialization."""
    assert developer_agent.agent_id == "developer_agent"
    capabilities = developer_agent.capabilities
    assert capabilities["can_write_code"] is True
    assert capabilities["can_parse_architecture"] is True
    assert capabilities["can_parse_uiux"] is True
    assert capabilities["can_create_tdd_strategy"] is True


@pytest.mark.asyncio
async def test_developer_agent_execute_mock_mode(developer_agent, mock_context):
    """Test DeveloperAgent execution in mock mode."""
    # Mock the config to enable mock mode
    from src.config import settings

    settings.llm_mode = "mock"

    # Mock the save_artifact method
    developer_agent.save_artifact = AsyncMock(return_value="artifact-123")
    developer_agent.log_event = AsyncMock()
    developer_agent.notify_completion = AsyncMock()

    # Create task
    task = AgentTask(
        task_id="task-1",
        task_type="development",
        input_data={
            "architecture": '{"system_overview": "test architecture"}',
            "ui_ux": '{"design_system": "test design"}',
            "prd": "Test PRD content",
        },
        dependencies=[],
        priority=5,
        metadata={},
    )

    # Execute
    result = await developer_agent.execute(task)

    # Assertions
    assert result.success is True
    assert result.task_id == "task-1"
    assert result.agent_id == "developer_agent"
    assert "development" in result.output
    assert "artifact_id" in result.output
    assert result.output["artifact_id"] == "artifact-123"
    assert result.output["next_stage"] == "qa_testing"

    # Verify development payload structure
    dev = result.output["development"]
    assert "tdd_strategy" in dev
    assert "development_phases" in dev
    assert "code_structure" in dev
    assert "testing_strategy" in dev
    assert "quality_gates" in dev
    assert "dependencies" in dev
    assert "development_workflow" in dev

    # Verify TDD strategy
    assert dev["tdd_strategy"]["approach"] == "test-first development"
    assert dev["tdd_strategy"]["test_framework"] == "pytest"
    assert dev["tdd_strategy"]["coverage_target"] == "80%"

    # Verify development phases
    assert len(dev["development_phases"]) > 0
    phase = dev["development_phases"][0]
    assert "phase" in phase
    assert "name" in phase
    assert "description" in phase
    assert "tdd_steps" in phase

    # Verify code structure
    assert "backend" in dev["code_structure"]
    assert "frontend" in dev["code_structure"]
    assert dev["code_structure"]["backend"]["language"] == "Python"
    assert dev["code_structure"]["backend"]["framework"] == "FastAPI"

    # Verify testing strategy
    assert "unit_tests" in dev["testing_strategy"]
    assert "integration_tests" in dev["testing_strategy"]
    assert "e2e_tests" in dev["testing_strategy"]

    # Verify artifact was saved
    developer_agent.save_artifact.assert_called_once()
    call_args = developer_agent.save_artifact.call_args
    assert call_args[1]["artifact_type"] == "development"
    assert "tdd_strategy" in call_args[1]["content"]


@pytest.mark.asyncio
async def test_developer_agent_missing_architecture(developer_agent):
    """Test DeveloperAgent with missing architecture input."""
    developer_agent.log_event = AsyncMock()
    developer_agent.notify_completion = AsyncMock()

    task = AgentTask(
        task_id="task-2",
        task_type="development",
        input_data={
            "architecture": "",  # Missing
            "ui_ux": '{"design_system": "test"}',
            "prd": "Test PRD",
        },
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await developer_agent.execute(task)

    assert result.success is False
    assert result.error == "Missing architecture content for development"


@pytest.mark.asyncio
async def test_developer_agent_with_real_llm(developer_agent, mock_context):
    """Test DeveloperAgent with real LLM mode (mocked response)."""
    from src.config import settings

    settings.llm_mode = "real"

    # Mock LLM response
    mock_llm_response = json.dumps(
        {
            "tdd_strategy": {
                "approach": "behavior-driven development",
                "test_framework": "jest",
                "coverage_target": "90%",
            },
            "development_phases": [
                {
                    "phase": 1,
                    "name": "Setup",
                    "description": "Initialize project",
                    "tdd_steps": ["Write setup tests", "Implement setup"],
                }
            ],
            "code_structure": {
                "backend": {"language": "Node.js", "framework": "Express", "structure": {}}
            },
            "testing_strategy": {
                "unit_tests": {"coverage": "All functions"},
                "integration_tests": {"coverage": "All APIs"},
                "e2e_tests": {"coverage": "Key flows"},
            },
            "quality_gates": {"pre_commit": ["linting"], "ci_pipeline": ["all tests"]},
            "dependencies": {"backend": ["express"], "frontend": ["react"]},
            "development_workflow": {"steps": ["Write test", "Implement", "Refactor"]},
        }
    )

    developer_agent.query_llm = AsyncMock(return_value=mock_llm_response)
    developer_agent.save_artifact = AsyncMock(return_value="artifact-456")
    developer_agent.log_event = AsyncMock()
    developer_agent.notify_completion = AsyncMock()

    task = AgentTask(
        task_id="task-3",
        task_type="development",
        input_data={
            "architecture": '{"system_overview": "microservices"}',
            "ui_ux": '{"design_system": "material"}',
            "prd": "Build a web app",
        },
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await developer_agent.execute(task)

    assert result.success is True
    assert result.output["development"]["tdd_strategy"]["approach"] == "behavior-driven development"
    assert result.output["development"]["code_structure"]["backend"]["language"] == "Node.js"

    # Verify LLM was called
    developer_agent.query_llm.assert_called_once()


@pytest.mark.asyncio
async def test_developer_agent_exception_handling(developer_agent):
    """Test DeveloperAgent exception handling."""
    developer_agent.log_event = AsyncMock()
    developer_agent.notify_completion = AsyncMock()
    developer_agent.save_artifact = AsyncMock(side_effect=Exception("Database error"))

    from src.config import settings

    settings.llm_mode = "mock"

    task = AgentTask(
        task_id="task-4",
        task_type="development",
        input_data={"architecture": '{"test": "data"}', "ui_ux": "", "prd": ""},
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await developer_agent.execute(task)

    assert result.success is False
    assert "Database error" in result.error

    # Verify error was logged
    developer_agent.log_event.assert_called()
    error_calls = [
        call for call in developer_agent.log_event.call_args_list if call[0][0] == "error"
    ]
    assert len(error_calls) > 0
