import json
import pytest

from src.agents.prd_agent import PRDAgent
from src.agents.base import AgentContext, AgentTask
from src.memory import MemoryStore
from src.skills.manager import SkillsManager


class FakeRedis:
    async def publish(self, channel, message):
        return None

    async def lpush(self, key, value):
        return None


class FakePool:
    def __init__(self):
        self.memory_rows = []

    class _Conn:
        def __init__(self, pool):
            self._pool = pool

        async def execute(self, *_args, **_kwargs):
            args = _args[1:] if _args else []
            if len(args) >= 4:
                doc_id, pattern_type, content, metadata = args[:4]
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)
                existing = next(
                    (row for row in self._pool.memory_rows if row["id"] == doc_id),
                    None,
                )
                record = {
                    "id": doc_id,
                    "pattern_type": pattern_type,
                    "content": content,
                    "metadata": metadata,
                }
                if existing:
                    existing.update(record)
                else:
                    self._pool.memory_rows.append(record)
            return None

        async def fetch(self, *_args, **_kwargs):
            return list(self._pool.memory_rows)

        async def fetchval(self, *_args, **_kwargs):
            return len(self._pool.memory_rows)

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
        project_id="proj",
        job_id="job",
        session_key="session",
        workspace_dir=str(tmp_path),
        redis_client=FakeRedis(),
        db_pool=FakePool(),
        anthropic_client=None,
        skills_manager=SkillsManager("./skills"),
        config={},
    )


@pytest.mark.asyncio
async def test_memory_store_deterministic_query():
    pool = FakePool()
    store = MemoryStore(db_pool=pool)

    await store.upsert_document("doc_a", "alpha beta gamma", {"pattern_type": "prd"})
    await store.upsert_document("doc_b", "alpha delta epsilon", {"pattern_type": "prd"})
    await store.upsert_document("doc_c", "theta iota kappa", {"pattern_type": "prd"})

    results_first = await store.query_similar("alpha beta", top_k=2, pattern_type="prd")
    results_second = await store.query_similar("alpha beta", top_k=2, pattern_type="prd")

    assert [item["id"] for item in results_first] == [item["id"] for item in results_second]
    assert results_first[0]["id"] == "doc_a"


@pytest.mark.asyncio
async def test_prd_agent_queries_memory_and_upserts(monkeypatch, tmp_path):
    calls = {"query": 0, "upsert": 0}

    class FakeMemoryStore:
        def __init__(self, *args, **kwargs):
            pass

        async def query_similar(self, *args, **kwargs):
            calls["query"] += 1
            return [{"id": "mem1", "text": "prior prd snippet", "metadata": {}, "score": 0.9}]

        async def upsert_document(self, *args, **kwargs):
            calls["upsert"] += 1
            return "mem1"

    monkeypatch.setattr("src.agents.prd_agent.MemoryStore", FakeMemoryStore)

    ctx = _make_context(tmp_path)
    agent = PRDAgent(ctx)

    async def _fake_query_llm(*_args, **_kwargs):
        return "PRD CONTENT"

    monkeypatch.setattr(agent, "query_llm", _fake_query_llm)

    task = AgentTask(
        task_id="task1",
        task_type="prd_generation",
        input_data={"requirements": "Build a payments dashboard"},
        dependencies=[],
        priority=5,
        metadata={},
    )

    result = await agent.execute(task)

    assert result.success is True
    assert calls["query"] == 1
    assert calls["upsert"] == 1
