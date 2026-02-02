"""Tests for ArchitectAgent."""

import pytest

from src.agents.base import AgentContext, AgentTask
from src.agents.architect_agent import ArchitectAgent
from src.skills.manager import SkillsManager


class FakeRedis:
    def __init__(self):
        self.published = []
        self.lpush_calls = []

    async def publish(self, channel, message):
        self.published.append((channel, message))

    async def lpush(self, key, value):
        self.lpush_calls.append((key, value))


class FakePool:
    def __init__(self):
        self.artifacts = []
        self.events = []

    class _Conn:
        def __init__(self, pool):
            self._pool = pool

        async def execute(self, query, *args, **kwargs):
            if "INSERT INTO artifacts" in query:
                self._pool.artifacts.append(args)
            elif "INSERT INTO agent_events" in query:
                self._pool.events.append(args)
            return None

        async def fetchval(self, query, *args, **kwargs):
            if "INSERT INTO artifacts" in query and "RETURNING id" in query:
                artifact_id = f"arch_{len(self._pool.artifacts)}"
                self._pool.artifacts.append(args)
                return artifact_id
            return None

    class _Acquire:
        def __init__(self, pool):
            self._pool = pool

        async def __aenter__(self):
            return FakePool._Conn(self._pool)

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def acquire(self):
        return FakePool._Acquire(self)


def _make_context(tmp_path):
    return AgentContext(
        project_id="test_proj",
        job_id="test_job",
        session_key="test_session",
        workspace_dir=str(tmp_path),
        redis_client=FakeRedis(),
        db_pool=FakePool(),
        anthropic_client=None,
        skills_manager=SkillsManager("./skills"),
        config={},
    )


@pytest.mark.asyncio
async def test_architect_agent_has_correct_id(tmp_path):
    """Test that ArchitectAgent has the correct agent ID."""
    ctx = _make_context(tmp_path)
    agent = ArchitectAgent(ctx)
    assert agent.agent_id == "architect_agent"


@pytest.mark.asyncio
async def test_architect_agent_capabilities(tmp_path):
    """Test that ArchitectAgent defines expected capabilities."""
    ctx = _make_context(tmp_path)
    agent = ArchitectAgent(ctx)
    caps = agent.capabilities

    assert caps["can_design_architecture"] is True
    assert caps["can_parse_prd"] is True
    assert caps["can_parse_plan"] is True
    assert "json" in caps["output_formats"]
    assert "markdown" in caps["output_formats"]


@pytest.mark.asyncio
async def test_architect_agent_execute_mock_mode(tmp_path):
    """Test ArchitectAgent execution in mock mode."""
    ctx = _make_context(tmp_path)
    agent = ArchitectAgent(ctx)

    task = AgentTask(
        task_id="task_123",
        task_type="architecture_design",
        input_data={"prd": "# PRD\nBuild a simple web app", "plan": '{"milestones": []}'},
        dependencies=[],
        priority=5,
        metadata={},
    )

    # Execute in mock mode (default)
    result = await agent.execute(task)

    assert result.success is True
    assert result.agent_id == "architect_agent"
    assert result.task_id == "task_123"
    assert "architecture" in result.output
    assert "artifact_id" in result.output
    assert len(result.artifacts) > 0

    # Verify architecture structure in mock mode
    architecture = result.output["architecture"]
    assert "system_overview" in architecture
    assert "components" in architecture
    assert "data_flows" in architecture
    assert "technology_stack" in architecture
    assert "deployment" in architecture

    # Verify components
    assert len(architecture["components"]) > 0
    comp = architecture["components"][0]
    assert "id" in comp
    assert "name" in comp
    assert "type" in comp
    assert "responsibilities" in comp


@pytest.mark.asyncio
async def test_architect_agent_missing_prd(tmp_path):
    """Test ArchitectAgent fails gracefully when PRD is missing."""
    ctx = _make_context(tmp_path)
    agent = ArchitectAgent(ctx)

    task = AgentTask(
        task_id="task_456",
        task_type="architecture_design",
        input_data={},  # Missing PRD
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)

    assert result.success is False
    assert "Missing PRD content" in result.error


@pytest.mark.asyncio
async def test_architect_agent_saves_artifact(tmp_path):
    """Test that ArchitectAgent saves architecture artifact."""
    ctx = _make_context(tmp_path)
    pool = ctx.db_pool
    agent = ArchitectAgent(ctx)

    task = AgentTask(
        task_id="task_789",
        task_type="architecture_design",
        input_data={"prd": "# PRD\nBuild an API service", "plan": ""},
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)

    assert result.success is True
    assert len(pool.artifacts) > 0


@pytest.mark.asyncio
async def test_architect_agent_metadata(tmp_path):
    """Test that ArchitectAgent includes metadata in result."""
    ctx = _make_context(tmp_path)
    agent = ArchitectAgent(ctx)

    task = AgentTask(
        task_id="task_999",
        task_type="architecture_design",
        input_data={"prd": "# PRD\nShort PRD", "plan": '{"milestones": [{"id": "m1"}]}'},
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)

    assert result.success is True
    assert result.metadata is not None
    assert "component_count" in result.metadata
    assert "parseable_json" in result.metadata
    assert result.metadata["parseable_json"] is True


def test_architect_agent_in_worker_registry():
    """Test that ArchitectAgent is registered in worker."""
    from src.workers.worker import AgentWorker

    worker = AgentWorker()
    registry = worker.agent_registry

    assert "architect_agent" in registry
    assert registry["architect_agent"] == ArchitectAgent
