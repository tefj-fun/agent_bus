"""Integration tests for agent skill permissions."""
import pytest

pytestmark = pytest.mark.skipif(True, reason="Requires database - run manually or in full integration tests")

import pytest
import asyncpg
from pathlib import Path
import tempfile
import shutil

from src.agents.base import BaseAgent, AgentContext, AgentTask, AgentResult
from src.skills import SkillsManager, SkillPermissionError


# Mock agent for testing
class TestAgent(BaseAgent):
    """Test agent for permission testing."""
    
    def get_agent_id(self) -> str:
        return "test_agent"
    
    def define_capabilities(self) -> dict:
        return {"can_test": True}
    
    async def execute(self, task: AgentTask) -> AgentResult:
        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            output={},
            artifacts=[]
        )


@pytest.fixture
async def db_pool():
    """Create test database pool."""
    pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        database="agent_bus_test",
        user="agent_bus",
        password="test_password",
        min_size=1,
        max_size=5
    )
    
    # Run migrations
    async with pool.acquire() as conn:
        # Run main schema
        with open('scripts/init_db.sql', 'r') as f:
            await conn.execute(f.read())
        
        # Run allowlist migration
        with open('scripts/migrations/001_add_skill_allowlists.sql', 'r') as f:
            await conn.execute(f.read())
    
    yield pool
    
    # Cleanup
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS agent_skill_allowlist CASCADE")
        await conn.execute("DROP TABLE IF EXISTS capability_skill_mapping CASCADE")
    
    await pool.close()


@pytest.fixture
def temp_skills_dir():
    """Create temporary skills directory with test skills."""
    temp_dir = tempfile.mkdtemp()
    
    # Create test skills
    skills = {
        "test-skill-1": {
            "skill.json": {
                "name": "test-skill-1",
                "version": "1.0.0",
                "description": "Test skill 1",
                "author": "Test",
                "capabilities": [{"name": "testing", "description": "Testing capability"}],
                "required_tools": [],
                "tags": ["test"]
            },
            "skill.md": "# Test Skill 1\n\nThis is a test skill."
        },
        "test-skill-2": {
            "skill.json": {
                "name": "test-skill-2",
                "version": "1.0.0",
                "description": "Test skill 2",
                "author": "Test",
                "capabilities": [{"name": "security", "description": "Security capability"}],
                "required_tools": [],
                "tags": ["security"]
            },
            "skill.md": "# Test Skill 2\n\nSecurity focused skill."
        },
        "forbidden-skill": {
            "skill.json": {
                "name": "forbidden-skill",
                "version": "1.0.0",
                "description": "Forbidden skill",
                "author": "Test",
                "capabilities": [],
                "required_tools": [],
                "tags": []
            },
            "skill.md": "# Forbidden Skill\n\nYou shall not pass."
        }
    }
    
    for skill_name, files in skills.items():
        skill_dir = Path(temp_dir) / skill_name
        skill_dir.mkdir()
        
        for filename, content in files.items():
            filepath = skill_dir / filename
            if filename.endswith('.json'):
                import json
                with open(filepath, 'w') as f:
                    json.dump(content, f, indent=2)
            else:
                with open(filepath, 'w') as f:
                    f.write(content)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
async def skills_manager(db_pool, temp_skills_dir):
    """Create SkillsManager with database pool."""
    manager = SkillsManager(skills_dir=temp_skills_dir, db_pool=db_pool)
    
    # Clear allowlist data
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM agent_skill_allowlist")
        await conn.execute("DELETE FROM capability_skill_mapping")
    
    if manager.allowlist_manager:
        manager.allowlist_manager.clear_cache()
    
    return manager


@pytest.fixture
async def agent_context(db_pool, skills_manager):
    """Create agent context for testing."""
    from anthropic import AsyncAnthropic
    import redis.asyncio as redis
    
    # Mock Redis
    redis_client = await redis.from_url("redis://localhost:6379/1")
    
    # Mock Anthropic client
    anthropic_client = AsyncAnthropic(api_key="test-key")
    
    context = AgentContext(
        project_id="test-project",
        job_id="test-job",
        session_key="test-session",
        workspace_dir="/tmp/test-workspace",
        redis_client=redis_client,
        db_pool=db_pool,
        anthropic_client=anthropic_client,
        skills_manager=skills_manager,
        config={}
    )
    
    yield context
    
    await redis_client.close()


class TestAgentSkillPermissions:
    """Test agent skill permission enforcement."""
    
    @pytest.mark.asyncio
    async def test_agent_load_skill_without_allowlist(self, agent_context):
        """Test agent can load any skill without allowlist entries."""
        agent = TestAgent(agent_context)
        
        # Should work (backward compatibility - no restrictions)
        skill = await agent.load_skill("test-skill-1")
        assert skill is not None
        assert skill.name == "test-skill-1"
    
    @pytest.mark.asyncio
    async def test_agent_load_allowed_skill(self, agent_context, db_pool):
        """Test agent can load explicitly allowed skill."""
        agent = TestAgent(agent_context)
        manager = agent_context.skills_manager.allowlist_manager
        
        # Allow test-skill-1
        await manager.add_allowlist_entry("test_agent", "test-skill-1", True)
        
        # Should work
        skill = await agent.load_skill("test-skill-1")
        assert skill is not None
    
    @pytest.mark.asyncio
    async def test_agent_load_denied_skill(self, agent_context, db_pool):
        """Test agent cannot load denied skill."""
        agent = TestAgent(agent_context)
        manager = agent_context.skills_manager.allowlist_manager
        
        # Deny forbidden-skill
        await manager.add_allowlist_entry("test_agent", "forbidden-skill", False)
        
        # Should raise SkillPermissionError
        with pytest.raises(SkillPermissionError) as exc_info:
            await agent.load_skill("forbidden-skill")
        
        assert "test_agent" in str(exc_info.value)
        assert "forbidden-skill" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_agent_load_skill_bypass_permissions(self, agent_context, db_pool):
        """Test agent can bypass permissions with enforce_permissions=False."""
        agent = TestAgent(agent_context)
        manager = agent_context.skills_manager.allowlist_manager
        
        # Deny skill
        await manager.add_allowlist_entry("test_agent", "forbidden-skill", False)
        
        # Should work with enforce_permissions=False
        skill = await agent.load_skill("forbidden-skill", enforce_permissions=False)
        assert skill is not None
    
    @pytest.mark.asyncio
    async def test_agent_wildcard_deny_with_specific_allow(self, agent_context, db_pool):
        """Test wildcard deny with specific skill allowed."""
        agent = TestAgent(agent_context)
        manager = agent_context.skills_manager.allowlist_manager
        
        # Deny all skills by default
        await manager.add_allowlist_entry("test_agent", "*", False)
        
        # Allow only test-skill-1
        await manager.add_allowlist_entry("test_agent", "test-skill-1", True)
        
        # Should work for allowed skill
        skill1 = await agent.load_skill("test-skill-1")
        assert skill1 is not None
        
        # Should fail for other skills
        with pytest.raises(SkillPermissionError):
            await agent.load_skill("test-skill-2")
    
    @pytest.mark.asyncio
    async def test_agent_find_skills_by_capability(self, agent_context, db_pool):
        """Test agent finding skills by capability with permission filter."""
        agent = TestAgent(agent_context)
        manager = agent_context.skills_manager.allowlist_manager
        
        # Add capability mappings
        await manager.add_capability_mapping("testing", "test-skill-1", 1)
        await manager.add_capability_mapping("testing", "test-skill-2", 2)
        
        # Restrict agent to test-skill-1 only
        await manager.add_allowlist_entry("test_agent", "*", False)
        await manager.add_allowlist_entry("test_agent", "test-skill-1", True)
        
        # Agent searches for testing capability
        skills = await agent.find_skills_by_capability("testing")
        
        # Should only get allowed skill
        assert skills == ["test-skill-1"]
    
    @pytest.mark.asyncio
    async def test_agent_get_allowed_skills(self, agent_context, db_pool):
        """Test agent getting list of allowed skills."""
        agent = TestAgent(agent_context)
        manager = agent_context.skills_manager.allowlist_manager
        
        # Add allowlist entries
        await manager.add_allowlist_entry("test_agent", "test-skill-1", True)
        await manager.add_allowlist_entry("test_agent", "test-skill-2", True)
        await manager.add_allowlist_entry("test_agent", "forbidden-skill", False)
        
        # Get allowed skills
        allowed = await agent.get_allowed_skills()
        
        assert "test-skill-1" in allowed
        assert "test-skill-2" in allowed
        assert "forbidden-skill" not in allowed
    
    @pytest.mark.asyncio
    async def test_execute_with_skill_permission_enforcement(self, agent_context, db_pool):
        """Test execute_with_skill respects permissions."""
        agent = TestAgent(agent_context)
        manager = agent_context.skills_manager.allowlist_manager
        
        # Deny forbidden-skill
        await manager.add_allowlist_entry("test_agent", "forbidden-skill", False)
        
        # Should raise permission error
        with pytest.raises(SkillPermissionError):
            await agent.execute_with_skill(
                "forbidden-skill",
                "Test prompt",
                {}
            )


class TestMultipleAgents:
    """Test permissions for multiple agents with different allowlists."""
    
    @pytest.mark.asyncio
    async def test_different_agents_different_permissions(
        self,
        agent_context,
        db_pool
    ):
        """Test that different agents have independent allowlists."""
        manager = agent_context.skills_manager.allowlist_manager
        
        # Agent 1: allowed to use test-skill-1
        await manager.add_allowlist_entry("agent_1", "*", False)
        await manager.add_allowlist_entry("agent_1", "test-skill-1", True)
        
        # Agent 2: allowed to use test-skill-2
        await manager.add_allowlist_entry("agent_2", "*", False)
        await manager.add_allowlist_entry("agent_2", "test-skill-2", True)
        
        # Create two agents with different IDs
        class Agent1(TestAgent):
            def get_agent_id(self) -> str:
                return "agent_1"
        
        class Agent2(TestAgent):
            def get_agent_id(self) -> str:
                return "agent_2"
        
        agent1 = Agent1(agent_context)
        agent2 = Agent2(agent_context)
        
        # Agent 1 can load test-skill-1
        skill = await agent1.load_skill("test-skill-1")
        assert skill is not None
        
        # Agent 1 cannot load test-skill-2
        with pytest.raises(SkillPermissionError):
            await agent1.load_skill("test-skill-2")
        
        # Agent 2 can load test-skill-2
        skill = await agent2.load_skill("test-skill-2")
        assert skill is not None
        
        # Agent 2 cannot load test-skill-1
        with pytest.raises(SkillPermissionError):
            await agent2.load_skill("test-skill-1")
