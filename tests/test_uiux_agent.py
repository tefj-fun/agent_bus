"""Tests for UIUXAgent."""

import pytest

from src.agents.base import AgentContext, AgentTask
from src.agents.uiux_agent import UIUXAgent
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
                artifact_id = f"uiux_{len(self._pool.artifacts)}"
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
async def test_uiux_agent_has_correct_id(tmp_path):
    """Test that UIUXAgent has the correct agent ID."""
    ctx = _make_context(tmp_path)
    agent = UIUXAgent(ctx)
    assert agent.agent_id == "uiux_agent"


@pytest.mark.asyncio
async def test_uiux_agent_capabilities(tmp_path):
    """Test that UIUXAgent defines expected capabilities."""
    ctx = _make_context(tmp_path)
    agent = UIUXAgent(ctx)
    caps = agent.capabilities

    assert caps["can_design_uiux"] is True
    assert caps["can_parse_architecture"] is True
    assert caps["can_create_design_system"] is True
    assert "json" in caps["output_formats"]
    assert "markdown" in caps["output_formats"]


@pytest.mark.asyncio
async def test_uiux_agent_execute_mock_mode(tmp_path):
    """Test UIUXAgent execution in mock mode."""
    ctx = _make_context(tmp_path)
    agent = UIUXAgent(ctx)

    task = AgentTask(
        task_id="task_123",
        task_type="uiux_design",
        input_data={"architecture": '{"components": []}', "prd": "# PRD\nBuild a simple web app"},
        dependencies=[],
        priority=5,
        metadata={},
    )

    # Execute in mock mode (default)
    result = await agent.execute(task)

    assert result.success is True
    assert result.agent_id == "uiux_agent"
    assert result.task_id == "task_123"
    assert "ui_ux" in result.output
    assert "artifact_id" in result.output
    assert len(result.artifacts) > 0

    # Verify UI/UX structure in mock mode
    ui_ux = result.output["ui_ux"]
    assert "design_system" in ui_ux
    assert "color_palette" in ui_ux
    assert "typography" in ui_ux
    assert "spacing" in ui_ux
    assert "components" in ui_ux
    assert "layouts" in ui_ux
    assert "user_flows" in ui_ux
    assert "accessibility" in ui_ux

    # Verify design system structure
    design_system = ui_ux["design_system"]
    assert "name" in design_system
    assert "version" in design_system
    assert "description" in design_system

    # Verify color palette
    colors = ui_ux["color_palette"]
    assert "primary" in colors
    assert "secondary" in colors
    assert "neutral" in colors

    # Verify components
    assert len(ui_ux["components"]) > 0
    comp = ui_ux["components"][0]
    assert "name" in comp
    assert "variants" in comp
    assert "states" in comp


@pytest.mark.asyncio
async def test_uiux_agent_missing_architecture(tmp_path):
    """Test UIUXAgent fails gracefully when architecture is missing."""
    ctx = _make_context(tmp_path)
    agent = UIUXAgent(ctx)

    task = AgentTask(
        task_id="task_456",
        task_type="uiux_design",
        input_data={},  # Missing architecture
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)

    assert result.success is False
    assert "Missing architecture content" in result.error


@pytest.mark.asyncio
async def test_uiux_agent_saves_artifact(tmp_path):
    """Test that UIUXAgent saves UI/UX artifact."""
    ctx = _make_context(tmp_path)
    pool = ctx.db_pool
    agent = UIUXAgent(ctx)

    task = AgentTask(
        task_id="task_789",
        task_type="uiux_design",
        input_data={
            "architecture": '{"components": [{"name": "API"}]}',
            "prd": "# PRD\nBuild an API service",
        },
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)

    assert result.success is True
    assert len(pool.artifacts) > 0


@pytest.mark.asyncio
async def test_uiux_agent_metadata(tmp_path):
    """Test that UIUXAgent includes metadata in result."""
    ctx = _make_context(tmp_path)
    agent = UIUXAgent(ctx)

    task = AgentTask(
        task_id="task_999",
        task_type="uiux_design",
        input_data={"architecture": '{"components": []}', "prd": "# PRD\nShort PRD"},
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


def test_uiux_agent_in_worker_registry():
    """Test that UIUXAgent is registered in worker."""
    from src.workers.worker import AgentWorker

    worker = AgentWorker()
    registry = worker.agent_registry

    assert "uiux_agent" in registry
    assert registry["uiux_agent"] == UIUXAgent
