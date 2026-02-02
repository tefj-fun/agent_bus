import json
import pathlib

import pytest


def test_no_eval_left_in_repo():
    # Basic safety check: eval() should not be used for task payloads/results.
    root = pathlib.Path(__file__).resolve().parents[1]
    py_files = list(root.rglob("*.py"))
    offenders = []
    for p in py_files:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        # allow this test file itself to contain the string "eval("
        if p.name == "test_phase1_plumbing.py":
            continue
        if "eval(" in txt:
            offenders.append(str(p.relative_to(root)))
    assert offenders == [], f"Found eval() usage in: {offenders}"


class FakeRedis:
    def __init__(self):
        self.published = []
        self.setex_calls = []

    async def publish(self, channel, message):
        self.published.append((channel, message))

    async def setex(self, key, ttl, value):
        self.setex_calls.append((key, ttl, value))


class FakePool:
    class _Conn:
        async def execute(self, *args, **kwargs):
            return None

    class _Acquire:
        async def __aenter__(self):
            return FakePool._Conn()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def acquire(self):
        return FakePool._Acquire()


@pytest.mark.asyncio
async def test_notify_completion_does_not_write_results_key():
    from src.agents.base import BaseAgent, AgentContext, AgentResult
    from src.skills.manager import SkillsManager

    class DummyAgent(BaseAgent):
        def get_agent_id(self) -> str:
            return "dummy"

        def define_capabilities(self):
            return {}

        async def execute(self, task):
            raise NotImplementedError

    r = FakeRedis()
    ctx = AgentContext(
        project_id="p",
        job_id="j",
        session_key="s",
        workspace_dir="/tmp",
        redis_client=r,
        db_pool=FakePool(),
        anthropic_client=None,
        skills_manager=SkillsManager("./skills"),
        config={},
    )
    agent = DummyAgent(ctx)

    result = AgentResult(
        task_id="task_123",
        agent_id="dummy",
        success=True,
        output={"ok": True},
        artifacts=[],
    )

    await agent.notify_completion(result)

    # It should publish a JSON payload...
    assert r.published, "Expected publish() to be called"
    channel, payload = r.published[0]
    assert channel == "agent_bus:events:task_completed"
    json.loads(payload)

    # ...but MUST NOT set the master result key.
    assert r.setex_calls == [], "notify_completion must not write agent_bus:results:*"
