"""Tests for skill allowlist and capability mapping system."""

import pytest
import asyncpg
from src.skills.allowlist import (
    SkillAllowlistManager,
    SkillPermissionError,
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
    
    # Run migration
    async with pool.acquire() as conn:
        with open('scripts/migrations/001_add_skill_allowlists.sql', 'r') as f:
            await conn.execute(f.read())
    
    yield pool
    
    # Cleanup
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS agent_skill_allowlist CASCADE")
        await conn.execute("DROP TABLE IF EXISTS capability_skill_mapping CASCADE")
    
    await pool.close()


@pytest.fixture
async def allowlist_manager(db_pool):
    """Create allowlist manager instance."""
    manager = SkillAllowlistManager(db_pool)
    
    # Clear data before each test
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM agent_skill_allowlist")
        await conn.execute("DELETE FROM capability_skill_mapping")
    
    manager.clear_cache()
    
    return manager


class TestSkillAllowlist:
    """Test skill allowlist functionality."""
    
    @pytest.mark.asyncio
    async def test_default_allow_all(self, allowlist_manager):
        """Test that agents without allowlist entries can use any skill."""
        # No entries = allow all (backward compatibility)
        assert await allowlist_manager.check_permission("developer_agent", "any-skill")
        assert await allowlist_manager.check_permission("qa_agent", "another-skill")
    
    @pytest.mark.asyncio
    async def test_explicit_allow(self, allowlist_manager):
        """Test explicit skill allowlist entry."""
        # Add explicit allow entry
        await allowlist_manager.add_allowlist_entry(
            agent_id="developer_agent",
            skill_name="code-analyzer",
            allowed=True,
            notes="Test allow"
        )
        
        # Should be allowed
        assert await allowlist_manager.check_permission("developer_agent", "code-analyzer")
    
    @pytest.mark.asyncio
    async def test_explicit_deny(self, allowlist_manager):
        """Test explicit skill denial."""
        # Add deny entry
        await allowlist_manager.add_allowlist_entry(
            agent_id="qa_agent",
            skill_name="dangerous-skill",
            allowed=False,
            notes="Test deny"
        )
        
        # Should be denied
        assert not await allowlist_manager.check_permission("qa_agent", "dangerous-skill")
    
    @pytest.mark.asyncio
    async def test_wildcard_allow(self, allowlist_manager):
        """Test wildcard allow entry."""
        # Add wildcard allow
        await allowlist_manager.add_allowlist_entry(
            agent_id="developer_agent",
            skill_name="*",
            allowed=True
        )
        
        # All skills should be allowed
        assert await allowlist_manager.check_permission("developer_agent", "skill-1")
        assert await allowlist_manager.check_permission("developer_agent", "skill-2")
        assert await allowlist_manager.check_permission("developer_agent", "skill-3")
    
    @pytest.mark.asyncio
    async def test_wildcard_deny_with_explicit_allow(self, allowlist_manager):
        """Test wildcard deny with specific skill allowed."""
        # Deny all by default
        await allowlist_manager.add_allowlist_entry(
            agent_id="security_agent",
            skill_name="*",
            allowed=False
        )
        
        # Allow specific skill
        await allowlist_manager.add_allowlist_entry(
            agent_id="security_agent",
            skill_name="security-audit",
            allowed=True
        )
        
        # Specific should override wildcard
        assert await allowlist_manager.check_permission("security_agent", "security-audit")
        
        # Others should be denied
        assert not await allowlist_manager.check_permission("security_agent", "other-skill")
    
    @pytest.mark.asyncio
    async def test_enforce_permission_success(self, allowlist_manager):
        """Test enforce_permission with allowed skill."""
        await allowlist_manager.add_allowlist_entry(
            agent_id="qa_agent",
            skill_name="pytest-gen",
            allowed=True
        )
        
        # Should not raise
        await allowlist_manager.enforce_permission("qa_agent", "pytest-gen")
    
    @pytest.mark.asyncio
    async def test_enforce_permission_denied(self, allowlist_manager):
        """Test enforce_permission with denied skill."""
        await allowlist_manager.add_allowlist_entry(
            agent_id="qa_agent",
            skill_name="forbidden-skill",
            allowed=False
        )
        
        # Should raise SkillPermissionError
        with pytest.raises(SkillPermissionError) as exc_info:
            await allowlist_manager.enforce_permission("qa_agent", "forbidden-skill")
        
        assert "qa_agent" in str(exc_info.value)
        assert "forbidden-skill" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_allowlist_entry(self, allowlist_manager):
        """Test updating an existing allowlist entry."""
        # Add initial entry
        entry_id = await allowlist_manager.add_allowlist_entry(
            agent_id="developer_agent",
            skill_name="test-skill",
            allowed=True
        )
        
        assert await allowlist_manager.check_permission("developer_agent", "test-skill")
        
        # Update to deny
        updated_id = await allowlist_manager.add_allowlist_entry(
            agent_id="developer_agent",
            skill_name="test-skill",
            allowed=False,
            notes="Changed to deny"
        )
        
        # Should be same entry ID
        assert entry_id == updated_id
        
        # Now should be denied
        assert not await allowlist_manager.check_permission("developer_agent", "test-skill")
    
    @pytest.mark.asyncio
    async def test_remove_allowlist_entry(self, allowlist_manager):
        """Test removing an allowlist entry."""
        # Add entry
        await allowlist_manager.add_allowlist_entry(
            agent_id="qa_agent",
            skill_name="temp-skill",
            allowed=False
        )
        
        assert not await allowlist_manager.check_permission("qa_agent", "temp-skill")
        
        # Remove it
        removed = await allowlist_manager.remove_allowlist_entry("qa_agent", "temp-skill")
        assert removed
        
        # Should revert to default (allow)
        assert await allowlist_manager.check_permission("qa_agent", "temp-skill")
    
    @pytest.mark.asyncio
    async def test_get_agent_allowed_skills(self, allowlist_manager):
        """Test getting all allowed skills for an agent."""
        # Add multiple entries
        await allowlist_manager.add_allowlist_entry("developer_agent", "skill-1", True)
        await allowlist_manager.add_allowlist_entry("developer_agent", "skill-2", True)
        await allowlist_manager.add_allowlist_entry("developer_agent", "skill-3", False)
        
        allowed = await allowlist_manager.get_agent_allowed_skills("developer_agent")
        
        assert "skill-1" in allowed
        assert "skill-2" in allowed
        assert "skill-3" not in allowed
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, allowlist_manager):
        """Test that cache is invalidated on updates."""
        # Add entry
        await allowlist_manager.add_allowlist_entry(
            agent_id="qa_agent",
            skill_name="cache-test",
            allowed=True
        )
        
        # Check once (populates cache)
        assert await allowlist_manager.check_permission("qa_agent", "cache-test")
        
        # Update entry
        await allowlist_manager.add_allowlist_entry(
            agent_id="qa_agent",
            skill_name="cache-test",
            allowed=False
        )
        
        # Should reflect new value (cache invalidated)
        assert not await allowlist_manager.check_permission("qa_agent", "cache-test")


class TestCapabilityMapping:
    """Test capability-to-skill mapping functionality."""
    
    @pytest.mark.asyncio
    async def test_add_capability_mapping(self, allowlist_manager):
        """Test adding capability mapping."""
        mapping_id = await allowlist_manager.add_capability_mapping(
            capability_name="ui-design",
            skill_name="ui-ux-pro-max",
            priority=1,
            metadata={"version": "1.0.0"}
        )
        
        assert mapping_id > 0
    
    @pytest.mark.asyncio
    async def test_get_skills_by_capability(self, allowlist_manager):
        """Test finding skills by capability."""
        # Add mappings with different priorities
        await allowlist_manager.add_capability_mapping("testing", "pytest-gen", 1)
        await allowlist_manager.add_capability_mapping("testing", "jest-gen", 5)
        await allowlist_manager.add_capability_mapping("testing", "cypress", 10)
        
        skills = await allowlist_manager.get_skills_by_capability("testing")
        
        # Should be ordered by priority (ascending)
        assert skills == ["pytest-gen", "jest-gen", "cypress"]
    
    @pytest.mark.asyncio
    async def test_get_skills_by_capability_with_permission_filter(self, allowlist_manager):
        """Test capability search filtered by agent permissions."""
        # Add capability mappings
        await allowlist_manager.add_capability_mapping("security", "sec-audit", 1)
        await allowlist_manager.add_capability_mapping("security", "vuln-scan", 2)
        await allowlist_manager.add_capability_mapping("security", "pen-test", 3)
        
        # Security agent can only use sec-audit and vuln-scan
        await allowlist_manager.add_allowlist_entry("security_agent", "*", False)
        await allowlist_manager.add_allowlist_entry("security_agent", "sec-audit", True)
        await allowlist_manager.add_allowlist_entry("security_agent", "vuln-scan", True)
        
        # Get skills for capability filtered by agent
        skills = await allowlist_manager.get_skills_by_capability(
            "security",
            agent_id="security_agent"
        )
        
        # Should only include allowed skills
        assert skills == ["sec-audit", "vuln-scan"]
        assert "pen-test" not in skills
    
    @pytest.mark.asyncio
    async def test_update_capability_mapping(self, allowlist_manager):
        """Test updating capability mapping priority."""
        # Add initial mapping
        await allowlist_manager.add_capability_mapping("doc", "tech-writer", 10)
        
        skills = await allowlist_manager.get_skills_by_capability("doc")
        assert skills == ["tech-writer"]
        
        # Update priority (should upsert)
        await allowlist_manager.add_capability_mapping("doc", "tech-writer", 1)
        
        # Add another skill
        await allowlist_manager.add_capability_mapping("doc", "api-doc-gen", 5)
        
        skills = await allowlist_manager.get_skills_by_capability("doc")
        assert skills == ["tech-writer", "api-doc-gen"]
    
    @pytest.mark.asyncio
    async def test_remove_capability_mapping(self, allowlist_manager):
        """Test removing capability mapping."""
        # Add mapping
        await allowlist_manager.add_capability_mapping("testing", "old-tool", 1)
        
        skills = await allowlist_manager.get_skills_by_capability("testing")
        assert "old-tool" in skills
        
        # Remove it
        removed = await allowlist_manager.remove_capability_mapping("testing", "old-tool")
        assert removed
        
        skills = await allowlist_manager.get_skills_by_capability("testing")
        assert "old-tool" not in skills
    
    @pytest.mark.asyncio
    async def test_get_all_capabilities(self, allowlist_manager):
        """Test getting list of all capabilities."""
        # Add various mappings
        await allowlist_manager.add_capability_mapping("ui-design", "figma", 1)
        await allowlist_manager.add_capability_mapping("testing", "pytest", 1)
        await allowlist_manager.add_capability_mapping("security", "audit", 1)
        await allowlist_manager.add_capability_mapping("ui-design", "sketch", 2)
        
        capabilities = await allowlist_manager.get_all_capabilities()
        
        # Should be unique and sorted
        assert set(capabilities) == {"ui-design", "testing", "security"}
    
    @pytest.mark.asyncio
    async def test_capability_cache_invalidation(self, allowlist_manager):
        """Test that capability cache is invalidated on updates."""
        # Add mapping
        await allowlist_manager.add_capability_mapping("cache-test", "skill-1", 1)
        
        # Fetch once (populates cache)
        skills = await allowlist_manager.get_skills_by_capability("cache-test")
        assert skills == ["skill-1"]
        
        # Add another skill
        await allowlist_manager.add_capability_mapping("cache-test", "skill-2", 2)
        
        # Should include new skill (cache invalidated)
        skills = await allowlist_manager.get_skills_by_capability("cache-test")
        assert skills == ["skill-1", "skill-2"]


class TestIntegration:
    """Integration tests combining allowlists and capabilities."""
    
    @pytest.mark.asyncio
    async def test_restricted_agent_capability_discovery(self, allowlist_manager):
        """Test full workflow: agent discovers skills via capability."""
        # Setup capability mappings
        await allowlist_manager.add_capability_mapping("ui-design", "figma-pro", 1)
        await allowlist_manager.add_capability_mapping("ui-design", "sketch-tool", 2)
        await allowlist_manager.add_capability_mapping("ui-design", "basic-ui", 10)
        
        # Setup agent allowlist (only figma-pro and basic-ui)
        await allowlist_manager.add_allowlist_entry("uiux_agent", "*", False)
        await allowlist_manager.add_allowlist_entry("uiux_agent", "figma-pro", True)
        await allowlist_manager.add_allowlist_entry("uiux_agent", "basic-ui", True)
        
        # Agent requests ui-design capability
        skills = await allowlist_manager.get_skills_by_capability(
            "ui-design",
            agent_id="uiux_agent"
        )
        
        # Should only get allowed skills, in priority order
        assert skills == ["figma-pro", "basic-ui"]
        
        # Verify permissions directly
        assert await allowlist_manager.check_permission("uiux_agent", "figma-pro")
        assert not await allowlist_manager.check_permission("uiux_agent", "sketch-tool")
        assert await allowlist_manager.check_permission("uiux_agent", "basic-ui")
