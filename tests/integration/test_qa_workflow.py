"""Integration test for QA workflow stage."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from src.orchestration.workflow import WorkflowStage
from src.agents.qa_agent import QAAgent
from src.agents.base import AgentContext, AgentTask


@pytest.mark.asyncio
async def test_qa_stage_in_workflow():
    """Test that QA stage is properly integrated in workflow."""
    from src.orchestration.workflow import WorkflowStateMachine
    
    workflow = WorkflowStateMachine()
    
    # Verify QA_TESTING stage exists
    assert WorkflowStage.QA_TESTING in WorkflowStage
    
    # Verify Development can transition to QA_TESTING
    next_stages = workflow.get_next_stages(WorkflowStage.DEVELOPMENT)
    assert WorkflowStage.QA_TESTING in next_stages
    
    # Verify QA_TESTING is mapped to qa_agent
    agent_id = workflow.get_agent_for_stage(WorkflowStage.QA_TESTING)
    assert agent_id == "qa_agent"
    
    # Verify QA_TESTING can transition to PM_REVIEW
    qa_next_stages = workflow.get_next_stages(WorkflowStage.QA_TESTING)
    assert WorkflowStage.PM_REVIEW in qa_next_stages


@pytest.mark.asyncio
async def test_qa_agent_with_development_output():
    """Test QA agent can process development stage output."""
    # Create mock context
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
    
    # Create QA agent
    qa_agent = QAAgent(context)
    qa_agent.save_artifact = AsyncMock(return_value="artifact-qa-integration")
    qa_agent.log_event = AsyncMock()
    qa_agent.notify_completion = AsyncMock()
    
    # Simulate development output
    development_output = {
        "tdd_strategy": {
            "approach": "test-first development",
            "test_framework": "pytest",
            "coverage_target": "80%"
        },
        "code_structure": {
            "backend": {
                "language": "Python",
                "framework": "FastAPI"
            }
        },
        "testing_strategy": {
            "unit_tests": {"coverage": "All business logic"},
            "integration_tests": {"coverage": "API endpoints"}
        }
    }
    
    # Create task with development output
    from src.config import settings
    settings.llm_mode = 'mock'
    
    task = AgentTask(
        task_id="integration-task-1",
        task_type="qa_testing",
        input_data={
            "development": json.dumps(development_output),
            "architecture": '{"system_type": "microservices"}',
            "prd": "Test application requirements"
        },
        dependencies=["development-task"],
        priority=5,
        metadata={}
    )
    
    # Execute QA agent
    result = await qa_agent.execute(task)
    
    # Verify successful execution
    assert result.success is True
    assert "qa" in result.output
    
    # Verify QA output contains test plans aligned with development
    qa_output = result.output["qa"]
    assert "test_plans" in qa_output
    assert len(qa_output["test_plans"]) > 0
    
    # Verify test plans include unit and integration testing
    test_plan_names = [p["name"] for p in qa_output["test_plans"]]
    assert any("unit" in name.lower() for name in test_plan_names)
    assert any("integration" in name.lower() for name in test_plan_names)
    
    # Verify QA strategy aligns with TDD approach
    assert "qa_strategy" in qa_output
    assert qa_output["qa_strategy"]["coverage_target"] in ["80%", "85%", "90%"]


@pytest.mark.asyncio
async def test_qa_artifact_storage():
    """Test that QA artifacts are properly stored."""
    # Create mock context with real-ish DB operations
    context = MagicMock(spec=AgentContext)
    context.project_id = "test-project"
    context.job_id = "test-job-artifact"
    context.session_key = "test-session"
    context.workspace_dir = "/tmp/workspace"
    context.redis_client = AsyncMock()
    
    # Mock DB pool
    mock_conn = AsyncMock()
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    context.db_pool = mock_pool
    
    context.anthropic_client = AsyncMock()
    context.skills_manager = MagicMock()
    context.config = {}
    
    # Create QA agent (use real save_artifact method)
    qa_agent = QAAgent(context)
    qa_agent.log_event = AsyncMock()
    qa_agent.notify_completion = AsyncMock()
    
    from src.config import settings
    settings.llm_mode = 'mock'
    
    task = AgentTask(
        task_id="artifact-task-1",
        task_type="qa_testing",
        input_data={
            "development": '{"tdd_strategy": "test-driven"}',
            "architecture": "",
            "prd": ""
        },
        dependencies=[],
        priority=5,
        metadata={}
    )
    
    # Execute
    result = await qa_agent.execute(task)
    
    # Verify artifact was saved
    assert result.success is True
    assert len(result.artifacts) > 0
    
    # Verify DB execute was called with correct artifact type
    mock_conn.execute.assert_called_once()
    call_args = mock_conn.execute.call_args[0]
    assert "artifacts" in call_args[0]  # SQL query
    assert "qa_agent" in call_args  # agent_id
    assert "test-job-artifact" in call_args  # job_id
    assert "qa" in call_args  # artifact type


@pytest.mark.asyncio
async def test_parallel_stage_support():
    """Test that QA can run in parallel with other stages."""
    from src.orchestration.workflow import WorkflowStateMachine
    
    workflow = WorkflowStateMachine()
    
    # Verify QA_TESTING is marked as parallel stage
    assert workflow.is_parallel_stage(WorkflowStage.QA_TESTING)
    
    # Verify parallel stages after development include QA
    parallel_stages = workflow.get_parallel_stages_after(WorkflowStage.DEVELOPMENT)
    assert WorkflowStage.QA_TESTING in parallel_stages
