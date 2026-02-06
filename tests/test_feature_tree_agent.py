"""Tests for FeatureTreeAgent."""

import pytest

from src.agents.base import AgentContext, AgentTask
from src.agents.feature_tree_agent import FeatureTreeAgent
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
async def test_feature_tree_agent_has_correct_id(tmp_path):
    ctx = _make_context(tmp_path)
    agent = FeatureTreeAgent(ctx)
    assert agent.agent_id == "feature_tree_agent"


@pytest.mark.asyncio
async def test_feature_tree_agent_capabilities(tmp_path):
    ctx = _make_context(tmp_path)
    agent = FeatureTreeAgent(ctx)
    caps = agent.capabilities

    assert caps["can_build_feature_tree"] is True
    assert caps["can_map_to_modules"] is True
    assert caps["can_enforce_modularization"] is True
    assert "json" in caps["output_formats"]
    assert "mermaid" in caps["output_formats"]


@pytest.mark.asyncio
async def test_feature_tree_agent_execute_mock_mode(tmp_path):
    from src.config import settings

    original_mode = settings.llm_mode
    settings.llm_mode = "mock"
    ctx = _make_context(tmp_path)
    agent = FeatureTreeAgent(ctx)

    task = AgentTask(
        task_id="task_123",
        task_type="feature_tree",
        input_data={"requirements": "Build a modular platform with auth and billing"},
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)
    settings.llm_mode = original_mode

    assert result.success is True
    assert result.agent_id == "feature_tree_agent"
    assert "feature_tree" in result.output
    assert "artifact_id" in result.output
    assert "graph_artifact_id" not in result.output
    assert len(result.artifacts) == 1

    payload = result.output["feature_tree"]
    assert "feature_tree" in payload
    assert "modularization_report" in payload
    assert payload["modularization_report"]["new_module_count"] == 0
    assert payload.get("mermaid")


def test_feature_tree_agent_extracts_json_from_code_fence(tmp_path):
    ctx = _make_context(tmp_path)
    agent = FeatureTreeAgent(ctx)
    payload = agent._extract_json(
        "```json\n{\"feature_tree\": [{\"id\": \"feat.core\"}]}\n```"
    )
    assert payload == {"feature_tree": [{"id": "feat.core"}]}


def test_feature_tree_agent_extracts_json_from_wrapped_text(tmp_path):
    ctx = _make_context(tmp_path)
    agent = FeatureTreeAgent(ctx)
    payload = agent._extract_json(
        "Here is the output:\n{\"feature_tree\": []}\nThanks!"
    )
    assert payload == {"feature_tree": []}


@pytest.mark.asyncio
async def test_feature_tree_agent_missing_inputs(tmp_path):
    ctx = _make_context(tmp_path)
    agent = FeatureTreeAgent(ctx)

    task = AgentTask(
        task_id="task_456",
        task_type="feature_tree",
        input_data={},
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)
    assert result.success is False
    assert "Missing requirements or PRD content" in result.error


def test_feature_tree_agent_in_worker_registry():
    from src.workers.worker import AgentWorker

    worker = AgentWorker()
    registry = worker.agent_registry

    assert "feature_tree_agent" in registry
    assert registry["feature_tree_agent"] == FeatureTreeAgent
