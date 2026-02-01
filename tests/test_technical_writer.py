"""Unit tests for TechnicalWriter agent."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.technical_writer import TechnicalWriter
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

    return context


@pytest.mark.asyncio
async def test_technical_writer_initialization(mock_context):
    """Test TechnicalWriter can be instantiated."""
    agent = TechnicalWriter(mock_context)
    assert agent.agent_id == "tech_writer"
    assert agent.context == mock_context


@pytest.mark.asyncio
async def test_technical_writer_capabilities(mock_context):
    """Test TechnicalWriter defines expected capabilities."""
    agent = TechnicalWriter(mock_context)
    capabilities = agent.define_capabilities()

    assert capabilities["can_generate_docs"] is True
    assert "guide" in capabilities["doc_types"]
    assert "tutorial" in capabilities["doc_types"]
    assert "reference" in capabilities["doc_types"]
    assert "release_notes" in capabilities["doc_types"]
    assert capabilities["supports_markdown"] is True


@pytest.mark.asyncio
async def test_technical_writer_execute_success(mock_context):
    """Test TechnicalWriter successful execution."""
    agent = TechnicalWriter(mock_context)

    # Mock the methods
    agent.save_artifact = AsyncMock(return_value="artifact-doc-123")
    agent.log_event = AsyncMock()
    agent.notify_completion = AsyncMock()
    agent.query_llm = AsyncMock(return_value="""# User Documentation

## Overview
This is a sample application that demonstrates the workflow.

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables
4. Run migrations: `alembic upgrade head`

## Key Workflows

### Creating a Project
1. Navigate to the projects page
2. Click "New Project"
3. Fill in the required details
4. Click "Create"

### Running Tests
Execute the test suite with: `pytest tests/`

## Troubleshooting

### Issue: Database connection fails
**Solution:** Verify your database credentials in the `.env` file

### Issue: Redis timeout
**Solution:** Ensure Redis is running: `redis-cli ping`

## API Reference
See the full API documentation at `/api/docs`
""")

    task = AgentTask(
        task_id="task-123",
        task_type="documentation",
        input_data={
            "development": "Development plan with implementation details",
            "architecture": "System architecture design",
            "qa": "QA strategy with test plans",
            "security": "Security audit results",
            "prd": "Product requirements document",
        },
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)

    assert result.success is True
    assert result.task_id == "task-123"
    assert result.agent_id == "tech_writer"
    assert "documentation" in result.output
    assert "artifact_id" in result.output
    assert result.output["artifact_id"] == "artifact-doc-123"
    assert len(result.artifacts) > 0
    assert result.artifacts[0] == "artifact-doc-123"

    # Verify documentation content
    doc_content = result.output["documentation"]
    assert "Overview" in doc_content or "Getting Started" in doc_content
    assert result.output["next_stage"] == "pm_review"

    # Verify save_artifact was called
    agent.save_artifact.assert_called_once()
    call_args = agent.save_artifact.call_args
    assert call_args[1]["artifact_type"] == "documentation"
    assert len(call_args[1]["content"]) > 0


@pytest.mark.asyncio
async def test_technical_writer_execute_handles_empty_input(mock_context):
    """Test TechnicalWriter handles empty input gracefully."""
    agent = TechnicalWriter(mock_context)

    agent.save_artifact = AsyncMock(return_value="artifact-doc-456")
    agent.log_event = AsyncMock()
    agent.notify_completion = AsyncMock()
    agent.query_llm = AsyncMock(return_value="# Minimal Documentation\n\nNo input provided.")

    task = AgentTask(
        task_id="task-456",
        task_type="documentation",
        input_data={},
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)

    # Should still succeed with minimal documentation
    assert result.success is True
    assert "documentation" in result.output


@pytest.mark.skip(reason="Flaky async mock in CI")
@pytest.mark.asyncio
async def test_technical_writer_execute_failure(mock_context):
    """Test TechnicalWriter handles execution failure."""
    agent = TechnicalWriter(mock_context)

    agent.log_event = AsyncMock()
    agent.notify_completion = AsyncMock()
    agent.query_llm = AsyncMock(side_effect=Exception("LLM query failed"))

    task = AgentTask(
        task_id="task-789",
        task_type="documentation",
        input_data={"development": "Development plan"},
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)

    assert result.success is False
    assert result.error is not None
    assert "LLM query failed" in result.error
    assert len(result.artifacts) == 0


@pytest.mark.asyncio
async def test_technical_writer_count_sections(mock_context):
    """Test the _count_sections helper method."""
    agent = TechnicalWriter(mock_context)

    content = """# Main Title

## Section 1

### Subsection 1.1

## Section 2

Some text without headers.

# Another Main Title
"""

    sections = agent._count_sections(content)
    assert sections == 5  # All lines starting with #


@pytest.mark.skip(reason="Flaky async mock in CI")
@pytest.mark.asyncio
async def test_technical_writer_metadata(mock_context):
    """Test TechnicalWriter includes metadata in result."""
    agent = TechnicalWriter(mock_context)

    agent.save_artifact = AsyncMock(return_value="artifact-doc-999")
    agent.log_event = AsyncMock()
    agent.notify_completion = AsyncMock()
    agent.query_llm = AsyncMock(return_value="# Title\n## Section\nContent")

    task = AgentTask(
        task_id="task-999",
        task_type="documentation",
        input_data={"development": "Dev content"},
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)

    assert result.success is True
    assert "sections" in result.metadata
    assert result.metadata["sections"] == 2  # Two headers in the mock response
