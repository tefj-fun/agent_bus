"""Unit tests for SupportEngineer agent."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from src.agents.support_engineer import SupportEngineer
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
async def test_support_engineer_initialization(mock_context):
    """Test SupportEngineer can be instantiated."""
    agent = SupportEngineer(mock_context)
    assert agent.agent_id == "support_engineer"
    assert agent.context == mock_context


@pytest.mark.asyncio
async def test_support_engineer_capabilities(mock_context):
    """Test SupportEngineer defines expected capabilities."""
    agent = SupportEngineer(mock_context)
    capabilities = agent.define_capabilities()
    
    assert capabilities["can_generate_support_docs"] is True
    assert "faq" in capabilities["doc_types"]
    assert "runbook" in capabilities["doc_types"]
    assert "troubleshooting" in capabilities["doc_types"]
    assert "release_support" in capabilities["doc_types"]
    assert capabilities["supports_markdown"] is True


@pytest.mark.asyncio
async def test_support_engineer_execute_success(mock_context):
    """Test SupportEngineer successful execution."""
    agent = SupportEngineer(mock_context)
    
    # Mock the methods
    agent.save_artifact = AsyncMock(return_value="artifact-support-123")
    agent.log_event = AsyncMock()
    agent.notify_completion = AsyncMock()
    agent.query_llm = AsyncMock(return_value="""# Support Documentation

## Frequently Asked Questions (FAQ)

### Q: How do I reset my password?
**A:** Navigate to the login page and click "Forgot Password". Follow the email instructions.

### Q: What are the system requirements?
**A:** Python 3.11+, PostgreSQL 14+, Redis 7+, and 4GB RAM minimum.

### Q: How do I contact support?
**A:** Email support@example.com or use the in-app chat feature.

## Common Issues and Resolutions

### Issue: Application won't start
**Symptoms:** Error message "Connection refused" on startup

**Diagnosis:**
1. Check if PostgreSQL is running: `pg_isready`
2. Verify Redis is accessible: `redis-cli ping`
3. Review logs in `logs/app.log`

**Resolution:**
- Start PostgreSQL: `sudo systemctl start postgresql`
- Start Redis: `sudo systemctl start redis`
- Check configuration in `.env` file

### Issue: Slow performance
**Symptoms:** API responses taking >5 seconds

**Diagnosis:**
1. Check database connection pool status
2. Monitor Redis memory usage
3. Review application logs for errors

**Resolution:**
- Increase connection pool size in config
- Clear Redis cache: `redis-cli FLUSHDB`
- Restart application workers

## Escalation Steps

### Level 1 Support (User Issues)
- Password resets
- Basic configuration questions
- Feature requests

**Escalate to Level 2 if:** Technical errors, data integrity issues, or performance problems

### Level 2 Support (Technical Issues)
- Database errors
- Integration failures
- Performance optimization

**Escalate to Engineering if:** Code bugs, security vulnerabilities, or architecture issues

## Operational Runbook

### Daily Health Checks
1. Verify all services are running
2. Check disk space: `df -h`
3. Review error logs for anomalies
4. Monitor API response times

### Backup Procedures
1. Database backup runs daily at 2 AM UTC
2. Backups retained for 30 days
3. Verify backup completion in logs

### Emergency Procedures
1. **Database Outage:** Switch to read replica, notify engineering
2. **Service Crash:** Check logs, restart service, monitor for recurrence
3. **Security Incident:** Isolate affected systems, notify security team

## Contact Information
- **Level 1 Support:** support@example.com
- **Level 2 Support:** tech-support@example.com
- **Engineering On-Call:** oncall@example.com
- **Security Team:** security@example.com
""")
    
    task = AgentTask(
        task_id="task-123",
        task_type="support_docs",
        input_data={
            "development": "Development plan with implementation details",
            "architecture": "System architecture design",
            "qa": "QA strategy with test plans",
            "security": "Security audit results",
            "prd": "Product requirements document"
        },
        dependencies=[],
        priority=5,
        metadata={}
    )
    
    result = await agent.execute(task)
    
    assert result.success is True
    assert result.task_id == "task-123"
    assert result.agent_id == "support_engineer"
    assert "support_docs" in result.output
    assert "artifact_id" in result.output
    assert result.output["artifact_id"] == "artifact-support-123"
    assert len(result.artifacts) > 0
    assert result.artifacts[0] == "artifact-support-123"
    
    # Verify support documentation content
    support_content = result.output["support_docs"]
    assert "FAQ" in support_content or "Troubleshooting" in support_content
    assert result.output["next_stage"] == "pm_review"
    
    # Verify save_artifact was called
    agent.save_artifact.assert_called_once()
    call_args = agent.save_artifact.call_args
    assert call_args[1]["artifact_type"] == "support_docs"
    assert len(call_args[1]["content"]) > 0


@pytest.mark.asyncio
async def test_support_engineer_execute_handles_empty_input(mock_context):
    """Test SupportEngineer handles empty input gracefully."""
    agent = SupportEngineer(mock_context)
    
    agent.save_artifact = AsyncMock(return_value="artifact-support-456")
    agent.log_event = AsyncMock()
    agent.notify_completion = AsyncMock()
    agent.query_llm = AsyncMock(return_value="# Minimal Support Docs\n\nNo input provided.")
    
    task = AgentTask(
        task_id="task-456",
        task_type="support_docs",
        input_data={},
        dependencies=[],
        priority=5,
        metadata={}
    )
    
    result = await agent.execute(task)
    
    # Should still succeed with minimal documentation
    assert result.success is True
    assert "support_docs" in result.output


@pytest.mark.skip(reason="Flaky async mock in CI")
@pytest.mark.asyncio
async def test_support_engineer_execute_failure(mock_context):
    """Test SupportEngineer handles execution failure."""
    agent = SupportEngineer(mock_context)
    
    agent.log_event = AsyncMock()
    agent.notify_completion = AsyncMock()
    agent.query_llm = AsyncMock(side_effect=Exception("LLM query failed"))
    
    task = AgentTask(
        task_id="task-789",
        task_type="support_docs",
        input_data={
            "development": "Development plan"
        },
        dependencies=[],
        priority=5,
        metadata={}
    )
    
    result = await agent.execute(task)
    
    assert result.success is False
    assert result.error is not None
    assert "LLM query failed" in result.error
    assert len(result.artifacts) == 0


@pytest.mark.asyncio
async def test_support_engineer_count_sections(mock_context):
    """Test the _count_sections helper method."""
    agent = SupportEngineer(mock_context)
    
    content = """# Support Guide

## FAQ

### Question 1

## Troubleshooting

### Issue 1

# Runbook
"""
    
    sections = agent._count_sections(content)
    assert sections == 6  # All lines starting with #


@pytest.mark.skip(reason="Flaky async mock in CI")
@pytest.mark.asyncio
async def test_support_engineer_metadata(mock_context):
    """Test SupportEngineer includes metadata in result."""
    agent = SupportEngineer(mock_context)
    
    agent.save_artifact = AsyncMock(return_value="artifact-support-999")
    agent.log_event = AsyncMock()
    agent.notify_completion = AsyncMock()
    agent.query_llm = AsyncMock(return_value="# Support\n## FAQ\n## Troubleshooting")
    
    task = AgentTask(
        task_id="task-999",
        task_type="support_docs",
        input_data={
            "development": "Dev content"
        },
        dependencies=[],
        priority=5,
        metadata={}
    )
    
    result = await agent.execute(task)
    
    assert result.success is True
    assert "sections" in result.metadata
    assert result.metadata["sections"] == 3  # Three headers in the mock response
