import pytest

from src.agents.base import AgentContext
from src.agents.technical_writer import TechnicalWriter
from src.agents.support_engineer import SupportEngineer
from src.agents.product_manager import ProductManager
from src.agents.project_manager import ProjectManager
from src.agents.memory_agent import MemoryAgent
from src.memory import MemoryStore
from src.skills.manager import SkillsManager
from src.workers.worker import AgentWorker


class FakeRedis:
    def __init__(self):
        self.published = []
        self.lpush_calls = []

    async def publish(self, channel, message):
        self.published.append((channel, message))

    async def lpush(self, key, value):
        self.lpush_calls.append((key, value))


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


def _make_context(tmp_path):
    return AgentContext(
        project_id="proj",
        job_id="job",
        session_key="session",
        workspace_dir=str(tmp_path),
        redis_client=FakeRedis(),
        db_pool=FakePool(),
        anthropic_client=None,
        skills_manager=SkillsManager("./skills"),
        config={"chroma_persist_directory": str(tmp_path / "chroma")},
    )


@pytest.mark.parametrize(
    "agent_cls, expected_id",
    [
        (TechnicalWriter, "tech_writer"),
        (SupportEngineer, "support_engineer"),
        (ProductManager, "product_manager"),
        (ProjectManager, "project_manager"),
        (MemoryAgent, "memory_agent"),
    ],
)
@pytest.mark.asyncio
async def test_phase2_agents_have_expected_ids(tmp_path, agent_cls, expected_id):
    ctx = _make_context(tmp_path)
    agent = agent_cls(ctx)
    assert agent.agent_id == expected_id


def test_worker_registry_includes_phase2_agents():
    worker = AgentWorker()
    registry = worker.agent_registry
    for agent_id in [
        "tech_writer",
        "support_engineer",
        "product_manager",
        "project_manager",
        "memory_agent",
    ]:
        assert agent_id in registry


def test_memory_store_health(tmp_path):
    store = MemoryStore(persist_directory=str(tmp_path / "chroma"))
    health = store.health()
    assert health["backend"] in {"chromadb", "memory"}
    assert health["count"] == 0
