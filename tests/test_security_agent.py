"""Unit tests for SecurityAgent."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from src.agents.security_agent import SecurityAgent
from src.agents.base import AgentContext, AgentTask


@pytest.fixture
def mock_context():
    """Create a mock agent context."""
    context = MagicMock(spec=AgentContext)
    context.project_id = "test-project"
    context.job_id = "test-job"
    context.session_key = "test-session"
    context.workspace_dir = "/tmp/test-workspace"
    context.redis_client = AsyncMock()
    context.db_pool = AsyncMock()
    context.anthropic_client = AsyncMock()
    context.skills_manager = MagicMock()
    context.config = {}
    
    # Mock database pool acquire
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value="artifact-id-123")
    context.db_pool.acquire = AsyncMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
    
    return context


@pytest.mark.asyncio
async def test_security_agent_initialization(mock_context):
    """Test SecurityAgent can be instantiated."""
    agent = SecurityAgent(mock_context)
    assert agent.agent_id == "security_agent"
    assert agent.context == mock_context


@pytest.mark.asyncio
async def test_security_agent_capabilities(mock_context):
    """Test SecurityAgent defines expected capabilities."""
    agent = SecurityAgent(mock_context)
    capabilities = agent.define_capabilities()
    
    assert capabilities["can_conduct_security_audit"] is True
    assert capabilities["can_identify_vulnerabilities"] is True
    assert capabilities["can_recommend_mitigations"] is True
    assert capabilities["can_assess_compliance"] is True
    assert "json" in capabilities["output_formats"]


@pytest.mark.asyncio
async def test_security_agent_execute_success(mock_context, monkeypatch):
    """Test SecurityAgent successful execution."""
    # Mock settings to use mock mode
    class MockSettings:
        llm_mode = 'mock'
    
    monkeypatch.setattr("src.agents.security_agent.settings", MockSettings())
    
    agent = SecurityAgent(mock_context)
    
    task = AgentTask(
        task_id="task-123",
        task_type="security_review",
        input_data={
            "development": "Development plan with TDD workflow",
            "architecture": "System architecture design",
            "qa": "QA strategy with test plans",
            "prd": "Product requirements document"
        },
        dependencies=[],
        priority=5,
        metadata={}
    )
    
    result = await agent.execute(task)
    
    assert result.success is True
    assert result.task_id == "task-123"
    assert result.agent_id == "security_agent"
    assert "security" in result.output
    assert "artifact_id" in result.output
    assert len(result.artifacts) > 0
    
    # Verify security audit structure
    security_data = result.output["security"]
    assert "security_audit" in security_data
    assert "vulnerabilities" in security_data
    assert "security_recommendations" in security_data
    assert "compliance_assessment" in security_data
    assert "security_best_practices" in security_data
    assert "security_metrics" in security_data
    
    # Verify vulnerabilities structure
    assert len(security_data["vulnerabilities"]) > 0
    vuln = security_data["vulnerabilities"][0]
    assert "vulnerability_id" in vuln
    assert "severity" in vuln
    assert "category" in vuln
    assert "title" in vuln
    assert "description" in vuln
    assert "recommendation" in vuln


@pytest.mark.asyncio
async def test_security_agent_missing_development_content(mock_context, monkeypatch):
    """Test SecurityAgent fails gracefully when development content is missing."""
    class MockSettings:
        llm_mode = 'mock'
    
    monkeypatch.setattr("src.agents.security_agent.settings", MockSettings())
    
    agent = SecurityAgent(mock_context)
    
    task = AgentTask(
        task_id="task-456",
        task_type="security_review",
        input_data={
            "development": "",  # Empty development content
            "architecture": "System architecture",
            "qa": "QA strategy"
        },
        dependencies=[],
        priority=5,
        metadata={}
    )
    
    result = await agent.execute(task)
    
    assert result.success is False
    assert result.error == "Missing development content for security review"


@pytest.mark.asyncio
async def test_security_agent_metadata(mock_context, monkeypatch):
    """Test SecurityAgent includes proper metadata in results."""
    class MockSettings:
        llm_mode = 'mock'
    
    monkeypatch.setattr("src.agents.security_agent.settings", MockSettings())
    
    agent = SecurityAgent(mock_context)
    
    task = AgentTask(
        task_id="task-789",
        task_type="security_review",
        input_data={
            "development": "Development plan content",
            "architecture": "Architecture content",
            "qa": "QA content",
            "prd": "PRD content"
        },
        dependencies=[],
        priority=5,
        metadata={}
    )
    
    result = await agent.execute(task)
    
    assert result.success is True
    assert "vulnerabilities_count" in result.metadata
    assert "recommendations_count" in result.metadata
    assert "parseable_json" in result.metadata
    assert result.metadata["parseable_json"] is True


@pytest.mark.asyncio
async def test_security_agent_vulnerability_categories(mock_context, monkeypatch):
    """Test SecurityAgent identifies various vulnerability categories."""
    class MockSettings:
        llm_mode = 'mock'
    
    monkeypatch.setattr("src.agents.security_agent.settings", MockSettings())
    
    agent = SecurityAgent(mock_context)
    
    task = AgentTask(
        task_id="task-999",
        task_type="security_review",
        input_data={
            "development": "Development plan",
            "architecture": "Architecture",
            "qa": "QA strategy"
        },
        dependencies=[],
        priority=5,
        metadata={}
    )
    
    result = await agent.execute(task)
    
    assert result.success is True
    security_data = result.output["security"]
    vulnerabilities = security_data["vulnerabilities"]
    
    # Check for various vulnerability categories
    categories = {v["category"] for v in vulnerabilities}
    assert len(categories) > 0
    
    # Verify at least some common categories are present
    common_categories = {"authentication", "injection", "access_control"}
    assert len(categories.intersection(common_categories)) > 0


@pytest.mark.asyncio
async def test_security_agent_compliance_assessment(mock_context, monkeypatch):
    """Test SecurityAgent includes compliance assessment."""
    class MockSettings:
        llm_mode = 'mock'
    
    monkeypatch.setattr("src.agents.security_agent.settings", MockSettings())
    
    agent = SecurityAgent(mock_context)
    
    task = AgentTask(
        task_id="task-comp",
        task_type="security_review",
        input_data={
            "development": "Development plan",
            "architecture": "Architecture"
        },
        dependencies=[],
        priority=5,
        metadata={}
    )
    
    result = await agent.execute(task)
    
    assert result.success is True
    security_data = result.output["security"]
    
    assert "compliance_assessment" in security_data
    compliance = security_data["compliance_assessment"]
    assert "standards_evaluated" in compliance
    assert "owasp_top_10_coverage" in compliance
    assert len(compliance["standards_evaluated"]) > 0
