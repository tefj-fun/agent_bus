"""Tests for allowlist configuration loader."""

import pytest

pytestmark = pytest.mark.skipif(True, reason="Requires database - run manually")

# ruff: noqa: E402
import asyncpg
import tempfile
import os

from src.skills.config_loader import AllowlistConfigLoader


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
        max_size=5,
    )

    # Run migration
    async with pool.acquire() as conn:
        with open("scripts/migrations/001_add_skill_allowlists.sql", "r") as f:
            await conn.execute(f.read())

    yield pool

    # Cleanup
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS agent_skill_allowlist CASCADE")
        await conn.execute("DROP TABLE IF EXISTS capability_skill_mapping CASCADE")

    await pool.close()


@pytest.fixture
async def config_loader(db_pool):
    """Create config loader instance."""
    loader = AllowlistConfigLoader(db_pool)

    # Clear data before each test
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM agent_skill_allowlist")
        await conn.execute("DELETE FROM capability_skill_mapping")

    loader.allowlist_manager.clear_cache()

    return loader


@pytest.fixture
def sample_config_yaml():
    """Create a sample YAML configuration."""
    yaml_content = """
agent_allowlists:
  developer_agent:
    - skill: "*"
      allowed: true
      notes: "Developer has full access"
  
  qa_agent:
    - skill: "pytest-gen"
      allowed: true
    - skill: "coverage-tool"
      allowed: true
    - skill: "*"
      allowed: false
      notes: "Only testing tools"

capability_mappings:
  testing:
    - skill: "pytest-gen"
      priority: 1
      metadata:
        framework: "pytest"
    - skill: "jest-gen"
      priority: 5
      metadata:
        framework: "jest"
  
  ui-design:
    - skill: "figma-pro"
      priority: 1
    - skill: "sketch-tool"
      priority: 10
"""

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


class TestConfigLoader:
    """Test YAML configuration loading."""

    @pytest.mark.asyncio
    async def test_load_from_yaml(self, config_loader, sample_config_yaml):
        """Test loading configuration from YAML file."""
        stats = await config_loader.load_from_yaml(sample_config_yaml)

        # Check stats
        assert stats["allowlist_entries"] == 4  # 2 for developer, 2 for qa
        assert stats["capability_mappings"] == 4  # 2 for testing, 2 for ui-design

    @pytest.mark.asyncio
    async def test_allowlist_entries_loaded(self, config_loader, sample_config_yaml):
        """Test that allowlist entries are correctly loaded."""
        await config_loader.load_from_yaml(sample_config_yaml)

        manager = config_loader.allowlist_manager

        # Check developer_agent
        assert await manager.check_permission("developer_agent", "any-skill")

        # Check qa_agent
        assert await manager.check_permission("qa_agent", "pytest-gen")
        assert await manager.check_permission("qa_agent", "coverage-tool")
        assert not await manager.check_permission("qa_agent", "other-skill")

    @pytest.mark.asyncio
    async def test_capability_mappings_loaded(self, config_loader, sample_config_yaml):
        """Test that capability mappings are correctly loaded."""
        await config_loader.load_from_yaml(sample_config_yaml)

        manager = config_loader.allowlist_manager

        # Check testing capability
        testing_skills = await manager.get_skills_by_capability("testing")
        assert testing_skills == ["pytest-gen", "jest-gen"]

        # Check ui-design capability
        ui_skills = await manager.get_skills_by_capability("ui-design")
        assert ui_skills == ["figma-pro", "sketch-tool"]

    @pytest.mark.asyncio
    async def test_clear_existing_on_load(self, config_loader, sample_config_yaml):
        """Test clearing existing entries before loading."""
        # Add some initial data
        await config_loader.allowlist_manager.add_allowlist_entry("old_agent", "old_skill", True)
        await config_loader.allowlist_manager.add_capability_mapping(
            "old_capability", "old_skill", 1
        )

        # Load with clear_existing=True
        await config_loader.load_from_yaml(sample_config_yaml, clear_existing=True)

        manager = config_loader.allowlist_manager

        # Old data should be gone
        skills = await manager.get_skills_by_capability("old_capability")
        assert len(skills) == 0

        # New data should be present
        assert await manager.check_permission("developer_agent", "any-skill")

    @pytest.mark.asyncio
    async def test_merge_on_load_without_clear(self, config_loader, sample_config_yaml):
        """Test merging new config with existing entries."""
        # Add some initial data
        await config_loader.allowlist_manager.add_allowlist_entry(
            "security_agent", "sec-tool", True
        )

        # Load without clear
        await config_loader.load_from_yaml(sample_config_yaml, clear_existing=False)

        manager = config_loader.allowlist_manager

        # Old data should still be there
        assert await manager.check_permission("security_agent", "sec-tool")

        # New data should also be there
        assert await manager.check_permission("developer_agent", "any-skill")

    @pytest.mark.asyncio
    async def test_invalid_yaml(self, config_loader):
        """Test handling of invalid YAML."""
        # Create temp file with invalid YAML
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                await config_loader.load_from_yaml(temp_path)
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_missing_file(self, config_loader):
        """Test handling of missing configuration file."""
        with pytest.raises(FileNotFoundError):
            await config_loader.load_from_yaml("/nonexistent/config.yaml")

    @pytest.mark.asyncio
    async def test_empty_config(self, config_loader):
        """Test loading empty configuration."""
        # Create empty YAML
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            stats = await config_loader.load_from_yaml(temp_path)
            assert stats["allowlist_entries"] == 0
            assert stats["capability_mappings"] == 0
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_export_to_yaml(self, config_loader, db_pool):
        """Test exporting configuration to YAML."""
        # Add some data
        manager = config_loader.allowlist_manager
        await manager.add_allowlist_entry("dev_agent", "skill-1", True, notes="Test")
        await manager.add_capability_mapping("cap-1", "skill-1", 1, {"key": "value"})

        # Export to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            export_path = f.name

        try:
            await config_loader.export_to_yaml(export_path)

            # Verify file exists and has content
            assert os.path.exists(export_path)

            with open(export_path, "r") as f:
                content = f.read()
                assert "dev_agent" in content
                assert "skill-1" in content
                assert "cap-1" in content
        finally:
            os.unlink(export_path)

    @pytest.mark.asyncio
    async def test_round_trip_export_import(self, config_loader, sample_config_yaml):
        """Test export-import round trip."""
        # Load initial config
        await config_loader.load_from_yaml(sample_config_yaml, clear_existing=True)

        # Export to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            export_path = f.name

        try:
            await config_loader.export_to_yaml(export_path)

            # Clear database
            async with db_pool.acquire() as conn:
                await conn.execute("DELETE FROM agent_skill_allowlist")
                await conn.execute("DELETE FROM capability_skill_mapping")

            # Re-import from exported file
            stats = await config_loader.load_from_yaml(export_path)

            # Should have same counts
            assert stats["allowlist_entries"] == 4
            assert stats["capability_mappings"] == 4

            # Verify data integrity
            manager = config_loader.allowlist_manager
            assert await manager.check_permission("developer_agent", "any-skill")
            assert await manager.check_permission("qa_agent", "pytest-gen")

            testing_skills = await manager.get_skills_by_capability("testing")
            assert "pytest-gen" in testing_skills
        finally:
            os.unlink(export_path)
