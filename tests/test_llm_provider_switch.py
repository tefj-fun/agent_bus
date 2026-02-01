import pytest

from src.agents.base import BaseAgent, AgentContext
from src.skills.manager import SkillsManager


class DummyAgent(BaseAgent):
    def get_agent_id(self) -> str:
        return "dummy"

    def define_capabilities(self):
        return {}

    async def execute(self, task):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_query_llm_routes_to_openai(monkeypatch):
    # Avoid requiring real infra; monkeypatch the provider call.
    from src.config import settings

    monkeypatch.setattr(settings, "llm_provider", "openai", raising=False)

    async def fake_openai_chat_complete(**kwargs):
        return "hello from openai"

    import src.infrastructure.openai_client as oc

    monkeypatch.setattr(oc, "openai_chat_complete", fake_openai_chat_complete)

    ctx = AgentContext(
        project_id="p",
        job_id="j",
        session_key="s",
        workspace_dir="/tmp",
        redis_client=None,  # unused
        db_pool=None,  # unused
        anthropic_client=None,  # unused
        skills_manager=SkillsManager("./skills"),
        config={},
    )

    agent = DummyAgent(ctx)
    out = await agent.query_llm(prompt="hi", system="sys", model="gpt-4o-mini")
    assert out == "hello from openai"
