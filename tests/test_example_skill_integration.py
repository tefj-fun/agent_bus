"""Integration tests for example skill (weather-toolkit) demonstrating skills system features."""

import pytest
import asyncpg
import json
import tempfile
from pathlib import Path

from src.skills import (
    SkillsManager,
    SkillAllowlistManager,
    SkillPermissionError,
    SkillLoadError,
)
from src.agents.base import BaseAgent, AgentContext, AgentTask, AgentResult


# Mock agent for testing skill integration
class WeatherAwareAgent(BaseAgent):
    """Test agent that uses weather capabilities."""
    
    def get_agent_id(self) -> str:
        return "weather_agent"
    
    def define_capabilities(self) -> dict:
        return {
            "weather-query": True,
            "weather-forecast": True,
        }
    
    async def execute(self, task: AgentTask) -> AgentResult:
        # In real implementation, would use loaded skills
        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            output={"message": "Weather query executed"},
            artifacts=[]
        )


class RestrictedAgent(BaseAgent):
    """Agent not allowed to use weather skills."""
    
    def get_agent_id(self) -> str:
        return "restricted_agent"
    
    def define_capabilities(self) -> dict:
        return {"basic": True}
    
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
        with open('scripts/migrations/001_add_skill_allowlists.sql', 'r') as f:
            await conn.execute(f.read())
    
    yield pool
    
    # Cleanup
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM agent_skill_allowlist")
        await conn.execute("DELETE FROM capability_skill_mapping")
    
    await pool.close()


@pytest.fixture
def example_skills_dir():
    """Create temporary directory with example skill."""
    temp_dir = tempfile.mkdtemp()
    
    # Create weather-toolkit skill
    skill_dir = Path(temp_dir) / "weather-toolkit"
    skill_dir.mkdir()
    
    # Copy the actual example skill files
    skill_json = {
        "name": "weather-toolkit",
        "version": "1.0.0",
        "description": "Weather data fetching and analysis toolkit",
        "author": "Agent Bus Example",
        "capabilities": [
            {
                "name": "weather-query",
                "description": "Fetch current weather conditions"
            },
            {
                "name": "weather-forecast",
                "description": "Get multi-day forecasts"
            },
            {
                "name": "weather-analysis",
                "description": "Analyze weather patterns"
            }
        ],
        "required_tools": [
            {"name": "web_fetch", "required": True},
            {"name": "exec", "required": False}
        ],
        "dependencies": [
            {"name": "requests", "version": ">=2.28.0", "optional": False}
        ],
        "entry_point": "skill.md",
        "min_python_version": "3.10",
        "repository": "https://github.com/example/weather-toolkit",
        "license": "MIT",
        "tags": ["weather", "data", "api", "example"],
        "metadata": {
            "example": True,
            "api_endpoint": "https://api.weather.gov"
        }
    }
    
    with open(skill_dir / "skill.json", "w") as f:
        json.dump(skill_json, f, indent=2)
    
    skill_md = """# Weather Toolkit

Example skill demonstrating Agent Bus skills system.

## Capabilities

- weather-query: Get current conditions
- weather-forecast: Get multi-day forecasts
- weather-analysis: Analyze patterns

## Usage

This skill integrates with NOAA Weather API.
"""
    
    with open(skill_dir / "skill.md", "w") as f:
        f.write(skill_md)
    
    yield temp_dir
    
    # Cleanup handled by tempfile


@pytest.fixture
async def skills_manager(example_skills_dir):
    """Create skills manager with example skill."""
    manager = SkillsManager(example_skills_dir)
    return manager


@pytest.fixture
async def allowlist_manager(db_pool):
    """Create allowlist manager."""
    manager = SkillAllowlistManager(db_pool)
    
    # Clear cache before each test
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM agent_skill_allowlist")
        await conn.execute("DELETE FROM capability_skill_mapping")
    
    manager.clear_cache()
    
    return manager


class TestExampleSkillLoading:
    """Test loading and validating the example skill."""
    
    @pytest.mark.asyncio
    async def test_load_weather_toolkit(self, skills_manager):
        """Test loading the weather-toolkit example skill."""
        skill = await skills_manager.load_skill("weather-toolkit")
        
        assert skill is not None
        assert skill.name == "weather-toolkit"
        assert skill.version == "1.0.0"
        assert skill.description == "Weather data fetching and analysis toolkit"
        assert skill.author == "Agent Bus Example"
    
    @pytest.mark.asyncio
    async def test_example_skill_capabilities(self, skills_manager):
        """Test that example skill has proper capabilities defined."""
        skill = await skills_manager.load_skill("weather-toolkit")
        
        assert len(skill.capabilities) == 3
        
        cap_names = [cap.name for cap in skill.capabilities]
        assert "weather-query" in cap_names
        assert "weather-forecast" in cap_names
        assert "weather-analysis" in cap_names
        
        # Verify capability descriptions
        query_cap = next(c for c in skill.capabilities if c.name == "weather-query")
        assert "current weather" in query_cap.description.lower()
    
    @pytest.mark.asyncio
    async def test_example_skill_tools(self, skills_manager):
        """Test that example skill declares tool requirements."""
        skill = await skills_manager.load_skill("weather-toolkit")
        
        assert len(skill.required_tools) == 2
        
        tool_names = [tool.name for tool in skill.required_tools]
        assert "web_fetch" in tool_names
        assert "exec" in tool_names
        
        # Verify required vs optional
        web_fetch = next(t for t in skill.required_tools if t.name == "web_fetch")
        assert web_fetch.required is True
        
        exec_tool = next(t for t in skill.required_tools if t.name == "exec")
        assert exec_tool.required is False
    
    @pytest.mark.asyncio
    async def test_example_skill_dependencies(self, skills_manager):
        """Test that example skill declares Python dependencies."""
        skill = await skills_manager.load_skill("weather-toolkit")
        
        assert len(skill.dependencies) > 0
        
        dep_names = [dep.name for dep in skill.dependencies]
        assert "requests" in dep_names
        
        requests_dep = next(d for d in skill.dependencies if d.name == "requests")
        assert requests_dep.version == ">=2.28.0"
        assert requests_dep.optional is False
    
    @pytest.mark.asyncio
    async def test_example_skill_metadata(self, skills_manager):
        """Test that example skill has proper metadata."""
        skill = await skills_manager.load_skill("weather-toolkit")
        
        assert skill.min_python_version == "3.10"
        assert skill.repository == "https://github.com/example/weather-toolkit"
        assert skill.license == "MIT"
        assert "weather" in skill.tags
        assert "example" in skill.tags
        
        # Custom metadata
        assert skill.metadata.get("example") is True
        assert "api.weather.gov" in skill.metadata.get("api_endpoint", "")
    
    @pytest.mark.asyncio
    async def test_example_skill_prompt(self, skills_manager):
        """Test that example skill loads prompt content."""
        skill = await skills_manager.load_skill("weather-toolkit")
        
        prompt = skill.get_prompt()
        assert prompt is not None
        assert len(prompt) > 0
        assert "Weather Toolkit" in prompt
        assert "weather-query" in prompt or "weather" in prompt.lower()


class TestCapabilityMapping:
    """Test capability-to-skill mapping with example skill."""
    
    @pytest.mark.asyncio
    async def test_map_weather_capabilities(self, allowlist_manager):
        """Test mapping weather capabilities to example skill."""
        # Map all three capabilities
        await allowlist_manager.add_capability_mapping(
            capability="weather-query",
            skill_name="weather-toolkit",
            priority=10
        )
        
        await allowlist_manager.add_capability_mapping(
            capability="weather-forecast",
            skill_name="weather-toolkit",
            priority=10
        )
        
        await allowlist_manager.add_capability_mapping(
            capability="weather-analysis",
            skill_name="weather-toolkit",
            priority=5
        )
        
        # Query should return weather-toolkit
        skills = await allowlist_manager.get_skills_for_capability("weather-query")
        assert len(skills) == 1
        assert skills[0] == "weather-toolkit"
        
        # Forecast capability
        skills = await allowlist_manager.get_skills_for_capability("weather-forecast")
        assert "weather-toolkit" in skills
    
    @pytest.mark.asyncio
    async def test_capability_priority_ordering(self, allowlist_manager):
        """Test that capabilities respect priority ordering."""
        # Add weather-toolkit with different priorities
        await allowlist_manager.add_capability_mapping(
            capability="data-fetch",
            skill_name="weather-toolkit",
            priority=5
        )
        
        await allowlist_manager.add_capability_mapping(
            capability="data-fetch",
            skill_name="other-toolkit",
            priority=10
        )
        
        # Higher priority should come first
        skills = await allowlist_manager.get_skills_for_capability("data-fetch")
        assert skills[0] == "other-toolkit"
        assert skills[1] == "weather-toolkit"
    
    @pytest.mark.asyncio
    async def test_multiple_skills_per_capability(self, allowlist_manager):
        """Test that multiple skills can provide same capability."""
        await allowlist_manager.add_capability_mapping(
            capability="weather-query",
            skill_name="weather-toolkit",
            priority=10
        )
        
        await allowlist_manager.add_capability_mapping(
            capability="weather-query",
            skill_name="alternate-weather",
            priority=8
        )
        
        skills = await allowlist_manager.get_skills_for_capability("weather-query")
        assert len(skills) == 2
        assert "weather-toolkit" in skills
        assert "alternate-weather" in skills


class TestPermissionEnforcement:
    """Test permission enforcement with example skill."""
    
    @pytest.mark.asyncio
    async def test_allow_agent_weather_skill(self, allowlist_manager):
        """Test allowing an agent to use weather-toolkit."""
        await allowlist_manager.add_allowlist_entry(
            agent_id="weather_agent",
            skill_name="weather-toolkit",
            allowed=True,
            notes="Weather agent needs weather capabilities"
        )
        
        allowed = await allowlist_manager.check_permission(
            "weather_agent",
            "weather-toolkit"
        )
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_deny_agent_weather_skill(self, allowlist_manager):
        """Test denying an agent access to weather-toolkit."""
        await allowlist_manager.add_allowlist_entry(
            agent_id="restricted_agent",
            skill_name="weather-toolkit",
            allowed=False,
            notes="Restricted agent should not access weather data"
        )
        
        allowed = await allowlist_manager.check_permission(
            "restricted_agent",
            "weather-toolkit"
        )
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_wildcard_skill_access(self, allowlist_manager):
        """Test wildcard access to all skills including weather-toolkit."""
        await allowlist_manager.add_allowlist_entry(
            agent_id="admin_agent",
            skill_name="*",
            allowed=True,
            notes="Admin has access to all skills"
        )
        
        # Should have access to weather-toolkit via wildcard
        allowed = await allowlist_manager.check_permission(
            "admin_agent",
            "weather-toolkit"
        )
        assert allowed is True
    
    @pytest.mark.asyncio
    async def test_specific_override_wildcard(self, allowlist_manager):
        """Test that specific deny overrides wildcard allow."""
        # Allow all
        await allowlist_manager.add_allowlist_entry(
            agent_id="test_agent",
            skill_name="*",
            allowed=True
        )
        
        # But deny weather-toolkit specifically
        await allowlist_manager.add_allowlist_entry(
            agent_id="test_agent",
            skill_name="weather-toolkit",
            allowed=False,
            notes="No weather access"
        )
        
        # Specific deny should win
        allowed = await allowlist_manager.check_permission(
            "test_agent",
            "weather-toolkit"
        )
        assert allowed is False


class TestSkillsManagerIntegration:
    """Test SkillsManager integration with permissions."""
    
    @pytest.mark.asyncio
    async def test_load_skill_with_permission(self, skills_manager, allowlist_manager, db_pool):
        """Test loading skill respects permissions."""
        # Give permission
        await allowlist_manager.add_allowlist_entry(
            agent_id="weather_agent",
            skill_name="weather-toolkit",
            allowed=True
        )
        
        # Create manager with allowlist
        manager_with_perms = SkillsManager(
            skills_manager.skills_directory,
            allowlist_manager=allowlist_manager
        )
        
        # Should succeed
        skill = await manager_with_perms.load_skill(
            "weather-toolkit",
            agent_id="weather_agent"
        )
        assert skill is not None
    
    @pytest.mark.asyncio
    async def test_load_skill_without_permission(self, skills_manager, allowlist_manager, db_pool):
        """Test loading skill fails without permission."""
        # Deny permission
        await allowlist_manager.add_allowlist_entry(
            agent_id="restricted_agent",
            skill_name="weather-toolkit",
            allowed=False
        )
        
        manager_with_perms = SkillsManager(
            skills_manager.skills_directory,
            allowlist_manager=allowlist_manager
        )
        
        # Should raise SkillPermissionError
        with pytest.raises(SkillPermissionError):
            await manager_with_perms.load_skill(
                "weather-toolkit",
                agent_id="restricted_agent"
            )
    
    @pytest.mark.asyncio
    async def test_load_skill_no_allowlist(self, skills_manager):
        """Test loading skill without allowlist (backward compatibility)."""
        # No allowlist = allow all
        skill = await skills_manager.load_skill(
            "weather-toolkit",
            agent_id="any_agent"
        )
        assert skill is not None


class TestEndToEndWorkflow:
    """End-to-end test demonstrating complete skills system workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_weather_skill_workflow(
        self,
        skills_manager,
        allowlist_manager,
        db_pool
    ):
        """
        Complete workflow:
        1. Load example skill
        2. Configure capability mappings
        3. Set up agent permissions
        4. Agent discovers and loads skill via capability
        5. Agent uses skill
        """
        # 1. Verify skill exists and loads
        skill = await skills_manager.load_skill("weather-toolkit")
        assert skill.name == "weather-toolkit"
        
        # 2. Configure capability mappings
        for cap in skill.capabilities:
            await allowlist_manager.add_capability_mapping(
                capability=cap.name,
                skill_name="weather-toolkit",
                priority=10
            )
        
        # 3. Grant weather_agent permission
        await allowlist_manager.add_allowlist_entry(
            agent_id="weather_agent",
            skill_name="weather-toolkit",
            allowed=True,
            notes="Weather agent needs weather capabilities"
        )
        
        # 4. Weather agent discovers skills via capability
        weather_skills = await allowlist_manager.get_skills_for_capability("weather-query")
        assert "weather-toolkit" in weather_skills
        
        # 5. Agent loads skill (with permission check)
        manager_with_perms = SkillsManager(
            skills_manager.skills_directory,
            allowlist_manager=allowlist_manager
        )
        
        loaded_skill = await manager_with_perms.load_skill(
            "weather-toolkit",
            agent_id="weather_agent"
        )
        
        assert loaded_skill is not None
        assert loaded_skill.get_prompt() is not None
        
        # Verify restricted agent cannot load
        await allowlist_manager.add_allowlist_entry(
            agent_id="restricted_agent",
            skill_name="weather-toolkit",
            allowed=False
        )
        
        with pytest.raises(SkillPermissionError):
            await manager_with_perms.load_skill(
                "weather-toolkit",
                agent_id="restricted_agent"
            )


class TestDocumentationQuality:
    """Test that example skill has high-quality documentation."""
    
    @pytest.mark.asyncio
    async def test_skill_has_complete_metadata(self, skills_manager):
        """Verify all important metadata fields are present."""
        skill = await skills_manager.load_skill("weather-toolkit")
        
        # Required fields
        assert skill.name
        assert skill.version
        assert skill.description
        assert skill.author
        
        # Recommended fields
        assert skill.repository
        assert skill.license
        assert len(skill.tags) > 0
        assert len(skill.capabilities) > 0
        
        # Best practice fields
        assert skill.min_python_version
        assert skill.entry_point
    
    @pytest.mark.asyncio
    async def test_capabilities_have_descriptions(self, skills_manager):
        """Verify all capabilities have meaningful descriptions."""
        skill = await skills_manager.load_skill("weather-toolkit")
        
        for cap in skill.capabilities:
            assert cap.description is not None
            assert len(cap.description) > 10  # Not just placeholder
            assert cap.description != cap.name
    
    @pytest.mark.asyncio
    async def test_prompt_has_usage_examples(self, skills_manager):
        """Verify skill prompt includes usage examples."""
        skill = await skills_manager.load_skill("weather-toolkit")
        prompt = skill.get_prompt()
        
        # Should contain implementation guidance
        assert "usage" in prompt.lower() or "example" in prompt.lower()
        assert len(prompt) > 500  # Substantial documentation
