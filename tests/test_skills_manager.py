"""Tests for skills manager and loader."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.skills import (
    SkillsManager,
    Skill,
    SkillLoadError,
    SkillNotFoundError,
    SkillRegistryError,
)


class TestSkillsManager:
    """Test SkillsManager class."""

    @pytest.mark.asyncio
    async def test_load_skill_with_skill_md(self):
        """Test loading skill with skill.md entry point."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skill
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test"
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            
            skill_content = "# Test Skill\n\nThis is a test skill."
            with open(skill_dir / "skill.md", "w") as f:
                f.write(skill_content)
            
            manager = SkillsManager(tmpdir)
            skill = await manager.load_skill("test-skill")
            
            assert skill is not None
            assert skill.name == "test-skill"
            assert skill.version == "1.0.0"
            assert skill.get_prompt() == skill_content

    @pytest.mark.asyncio
    async def test_load_skill_with_readme(self):
        """Test loading skill with README.md entry point."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test"
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            
            skill_content = "# Test Skill README"
            with open(skill_dir / "README.md", "w") as f:
                f.write(skill_content)
            
            manager = SkillsManager(tmpdir)
            skill = await manager.load_skill("test-skill")
            
            assert skill.get_prompt() == skill_content

    @pytest.mark.asyncio
    async def test_load_skill_with_custom_entry_point(self):
        """Test loading skill with custom entry point."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test",
                "entry_point": "custom.md"
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            
            skill_content = "# Custom Entry Point"
            with open(skill_dir / "custom.md", "w") as f:
                f.write(skill_content)
            
            manager = SkillsManager(tmpdir)
            skill = await manager.load_skill("test-skill")
            
            assert skill.get_prompt() == skill_content

    @pytest.mark.asyncio
    async def test_load_skill_caching(self):
        """Test that loaded skills are cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test"
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")
            
            manager = SkillsManager(tmpdir)
            
            # Load twice
            skill1 = await manager.load_skill("test-skill")
            skill2 = await manager.load_skill("test-skill")
            
            # Should return same instance
            assert skill1 is skill2

    @pytest.mark.asyncio
    async def test_load_skill_not_found(self):
        """Test loading non-existent skill raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillsManager(tmpdir)
            
            with pytest.raises(SkillNotFoundError) as exc_info:
                await manager.load_skill("nonexistent")
            
            assert "not found in registry" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_skill_no_content(self):
        """Test loading skill without content files raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test"
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            
            manager = SkillsManager(tmpdir)
            
            with pytest.raises(SkillLoadError) as exc_info:
                await manager.load_skill("test-skill")
            
            assert "No readable prompt content found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_skill_empty_content(self):
        """Test that empty content files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test"
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            
            # Create empty skill.md
            with open(skill_dir / "skill.md", "w") as f:
                f.write("")
            
            # Create valid README.md
            with open(skill_dir / "README.md", "w") as f:
                f.write("Valid content")
            
            manager = SkillsManager(tmpdir)
            skill = await manager.load_skill("test-skill")
            
            # Should skip empty skill.md and use README.md
            assert skill.get_prompt() == "Valid content"

    @pytest.mark.asyncio
    async def test_install_skill_success(self):
        """Test successful skill installation from git."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillsManager(tmpdir)
            
            skill_dir = Path(tmpdir) / "new-skill"
            
            # Mock git clone to create the skill after it's called
            def fake_git_clone(*args, **kwargs):
                # Create fake cloned skill after git clone is called
                skill_dir.mkdir()
                
                skill_json = {
                    "name": "new-skill",
                    "version": "1.0.0",
                    "description": "Test",
                    "author": "Test"
                }
                with open(skill_dir / "skill.json", "w") as f:
                    json.dump(skill_json, f)
                with open(skill_dir / "skill.md", "w") as f:
                    f.write("Test")
                
                return MagicMock(stdout="Cloning...", returncode=0)
            
            with patch('subprocess.run', side_effect=fake_git_clone) as mock_run:
                result = await manager.install_skill(
                    "https://github.com/test/skill",
                    "new-skill"
                )
                
                assert result is True
                mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_install_skill_already_exists(self):
        """Test installing skill that already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create existing skill
            skill_dir = Path(tmpdir) / "existing-skill"
            skill_dir.mkdir()
            
            manager = SkillsManager(tmpdir)
            
            with pytest.raises(SkillRegistryError) as exc_info:
                await manager.install_skill(
                    "https://github.com/test/skill",
                    "existing-skill"
                )
            
            assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_install_skill_git_failure(self):
        """Test handling git clone failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillsManager(tmpdir)
            
            with patch('subprocess.run') as mock_run:
                from subprocess import CalledProcessError
                mock_run.side_effect = CalledProcessError(
                    1, "git", stderr="Clone failed"
                )
                
                with pytest.raises(SkillRegistryError) as exc_info:
                    await manager.install_skill(
                        "https://github.com/test/skill",
                        "new-skill"
                    )
                
                assert "Git clone failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_install_skill_timeout(self):
        """Test handling git clone timeout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillsManager(tmpdir)
            
            with patch('subprocess.run') as mock_run:
                from subprocess import TimeoutExpired
                mock_run.side_effect = TimeoutExpired("git", 60)
                
                with pytest.raises(SkillRegistryError) as exc_info:
                    await manager.install_skill(
                        "https://github.com/test/skill",
                        "new-skill"
                    )
                
                assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_skill_success(self):
        """Test successful skill update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create existing skill
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test"
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")
            
            manager = SkillsManager(tmpdir)
            
            # Load skill first (to test cache clearing)
            await manager.load_skill("test-skill")
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    stdout="Already up to date.",
                    returncode=0
                )
                
                result = await manager.update_skill("test-skill")
                
                assert result is True
                # Verify cache was cleared
                assert "test-skill" not in manager.loaded_skills

    @pytest.mark.asyncio
    async def test_update_skill_not_found(self):
        """Test updating non-existent skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillsManager(tmpdir)
            
            with pytest.raises(SkillNotFoundError):
                await manager.update_skill("nonexistent")

    @pytest.mark.asyncio
    async def test_execute_skill(self):
        """Test executing a skill returns prompt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test"
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            
            skill_content = "Execute this skill"
            with open(skill_dir / "skill.md", "w") as f:
                f.write(skill_content)
            
            manager = SkillsManager(tmpdir)
            
            result = await manager.execute_skill("test-skill", {})
            
            assert result == skill_content

    def test_list_skills(self):
        """Test listing all skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two skills
            for i in range(2):
                skill_dir = Path(tmpdir) / f"skill-{i}"
                skill_dir.mkdir()
                
                skill_json = {
                    "name": f"skill-{i}",
                    "version": "1.0.0",
                    "description": "Test",
                    "author": "Test"
                }
                with open(skill_dir / "skill.json", "w") as f:
                    json.dump(skill_json, f)
                with open(skill_dir / "skill.md", "w") as f:
                    f.write("Test")
            
            manager = SkillsManager(tmpdir)
            skills = manager.list_skills()
            
            assert len(skills) == 2

    def test_get_skill_info(self):
        """Test getting skill info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test skill",
                "author": "Test Author"
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")
            
            manager = SkillsManager(tmpdir)
            info = manager.get_skill_info("test-skill")
            
            assert info is not None
            assert info.name == "test-skill"
            assert info.description == "Test skill"

    def test_reload_registry(self):
        """Test reloading registry clears cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test"
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")
            
            manager = SkillsManager(tmpdir)
            manager.loaded_skills["test-skill"] = MagicMock()
            
            manager.reload_registry()
            
            # Cache should be cleared
            assert len(manager.loaded_skills) == 0

    def test_get_skills_by_capability(self):
        """Test filtering skills by capability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test",
                "capabilities": [{"name": "testing"}]
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")
            
            manager = SkillsManager(tmpdir)
            skills = manager.get_skills_by_capability("testing")
            
            assert len(skills) == 1
            assert skills[0].name == "test-skill"

    def test_get_skills_by_tag(self):
        """Test filtering skills by tag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test",
                "tags": ["automation"]
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")
            
            manager = SkillsManager(tmpdir)
            skills = manager.get_skills_by_tag("automation")
            
            assert len(skills) == 1
            assert skills[0].name == "test-skill"


class TestSkill:
    """Test Skill class."""

    def test_skill_creation(self):
        """Test creating a Skill object."""
        from src.skills.registry import SkillMetadata
        
        metadata = SkillMetadata(
            name="test-skill",
            version="1.0.0",
            description="Test",
            author="Test"
        )
        
        content = "# Test Skill Content"
        skill = Skill(metadata, content)
        
        assert skill.name == "test-skill"
        assert skill.version == "1.0.0"
        assert skill.get_prompt() == content

    def test_skill_capabilities(self):
        """Test getting skill capabilities."""
        from src.skills.registry import SkillMetadata
        
        metadata = SkillMetadata(
            name="test-skill",
            version="1.0.0",
            description="Test",
            author="Test",
            capabilities=["testing", "automation"]
        )
        
        skill = Skill(metadata, "Test")
        capabilities = skill.get_capabilities()
        
        assert "testing" in capabilities
        assert "automation" in capabilities
