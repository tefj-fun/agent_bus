"""Tests for CLI skills management."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from src.cli import SkillsCLI, main


class TestSkillsCLI:
    """Test SkillsCLI class."""

    @pytest.mark.asyncio
    async def test_install_success(self):
        """Test successful skill installation via CLI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = SkillsCLI(tmpdir)
            
            skill_dir = Path(tmpdir) / "new-skill"
            
            def fake_git_clone(*args, **kwargs):
                skill_dir.mkdir()
                
                skill_json = {
                    "name": "new-skill",
                    "version": "1.0.0",
                    "description": "Test skill",
                    "author": "Test Author",
                    "capabilities": [{"name": "testing"}],
                    "tags": ["test"]
                }
                with open(skill_dir / "skill.json", "w") as f:
                    json.dump(skill_json, f)
                with open(skill_dir / "skill.md", "w") as f:
                    f.write("# Test Skill")
                
                return MagicMock(stdout="Cloning...", returncode=0)
            
            with patch('subprocess.run', side_effect=fake_git_clone):
                exit_code = await cli.install(
                    "https://github.com/test/new-skill",
                    "new-skill"
                )
                
                assert exit_code == 0
                assert skill_dir.exists()

    @pytest.mark.asyncio
    async def test_install_auto_name(self):
        """Test installation with auto-extracted name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = SkillsCLI(tmpdir)
            
            skill_dir = Path(tmpdir) / "auto-skill"
            
            def fake_git_clone(*args, **kwargs):
                skill_dir.mkdir()
                
                skill_json = {
                    "name": "auto-skill",
                    "version": "1.0.0",
                    "description": "Test",
                    "author": "Test"
                }
                with open(skill_dir / "skill.json", "w") as f:
                    json.dump(skill_json, f)
                with open(skill_dir / "skill.md", "w") as f:
                    f.write("Test")
                
                return MagicMock(stdout="Cloning...", returncode=0)
            
            with patch('subprocess.run', side_effect=fake_git_clone):
                # No skill_name provided, should extract from URL
                exit_code = await cli.install(
                    "https://github.com/test/auto-skill.git"
                )
                
                assert exit_code == 0

    @pytest.mark.asyncio
    async def test_install_already_exists(self):
        """Test installing skill that already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create existing skill
            skill_dir = Path(tmpdir) / "existing-skill"
            skill_dir.mkdir()
            
            cli = SkillsCLI(tmpdir)
            
            exit_code = await cli.install(
                "https://github.com/test/skill",
                "existing-skill"
            )
            
            assert exit_code == 1

    @pytest.mark.asyncio
    async def test_install_git_failure(self):
        """Test handling git clone failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = SkillsCLI(tmpdir)
            
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(
                    1, "git", stderr="Clone failed"
                )
                
                exit_code = await cli.install(
                    "https://github.com/test/skill",
                    "new-skill"
                )
                
                assert exit_code == 1

    @pytest.mark.asyncio
    async def test_update_success(self):
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
            
            cli = SkillsCLI(tmpdir)
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    stdout="Already up to date.",
                    returncode=0
                )
                
                exit_code = await cli.update("test-skill")
                
                assert exit_code == 0

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        """Test updating non-existent skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = SkillsCLI(tmpdir)
            
            exit_code = await cli.update("nonexistent")
            
            assert exit_code == 1

    def test_list_empty(self, capsys):
        """Test listing with no skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = SkillsCLI(tmpdir)
            
            exit_code = cli.list()
            
            assert exit_code == 0
            captured = capsys.readouterr()
            assert "No skills installed" in captured.out

    def test_list_skills(self, capsys):
        """Test listing skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test skills
            for i in range(2):
                skill_dir = Path(tmpdir) / f"skill-{i}"
                skill_dir.mkdir()
                
                skill_json = {
                    "name": f"skill-{i}",
                    "version": f"1.{i}.0",
                    "description": f"Test skill {i}",
                    "author": "Test"
                }
                with open(skill_dir / "skill.json", "w") as f:
                    json.dump(skill_json, f)
                with open(skill_dir / "skill.md", "w") as f:
                    f.write("Test")
            
            cli = SkillsCLI(tmpdir)
            
            exit_code = cli.list()
            
            assert exit_code == 0
            captured = capsys.readouterr()
            assert "skill-0" in captured.out
            assert "skill-1" in captured.out

    def test_list_verbose(self, capsys):
        """Test listing skills with verbose output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test skill",
                "author": "Test Author",
                "capabilities": [{"name": "testing"}],
                "tags": ["test", "automation"]
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")
            
            cli = SkillsCLI(tmpdir)
            
            exit_code = cli.list(verbose=True)
            
            assert exit_code == 0
            captured = capsys.readouterr()
            assert "Test Author" in captured.out
            assert "testing" in captured.out
            assert "test" in captured.out

    def test_info_success(self, capsys):
        """Test showing skill info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test skill",
                "author": "Test Author",
                "repository": "https://github.com/test/skill",
                "license": "MIT",
                "capabilities": [{"name": "testing"}],
                "required_tools": [{"name": "browser", "required": True}],
                "tags": ["test"],
                "dependencies": [{"name": "requests", "version": ">=2.0.0"}],
                "min_python_version": "3.10"
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")
            
            cli = SkillsCLI(tmpdir)
            
            exit_code = cli.info("test-skill")
            
            assert exit_code == 0
            captured = capsys.readouterr()
            assert "test-skill" in captured.out
            assert "1.0.0" in captured.out
            assert "Test Author" in captured.out
            assert "MIT" in captured.out
            assert "testing" in captured.out
            assert "browser" in captured.out
            assert "requests" in captured.out
            assert "3.10" in captured.out

    def test_info_not_found(self):
        """Test info for non-existent skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = SkillsCLI(tmpdir)
            
            exit_code = cli.info("nonexistent")
            
            assert exit_code == 1

    def test_extract_skill_name_basic(self):
        """Test extracting skill name from URL."""
        cli = SkillsCLI("./skills")
        
        name = cli._extract_skill_name("https://github.com/user/my-skill")
        assert name == "my-skill"

    def test_extract_skill_name_with_git(self):
        """Test extracting skill name from URL with .git."""
        cli = SkillsCLI("./skills")
        
        name = cli._extract_skill_name("https://github.com/user/my-skill.git")
        assert name == "my-skill"

    def test_extract_skill_name_underscore(self):
        """Test extracting skill name converts underscores."""
        cli = SkillsCLI("./skills")
        
        name = cli._extract_skill_name("https://github.com/user/my_skill")
        assert name == "my-skill"


class TestCLIMain:
    """Test main CLI entry point."""

    def test_main_no_args(self, capsys):
        """Test CLI with no arguments shows help."""
        with patch('sys.argv', ['agent-bus-skills']):
            exit_code = main()
            
            assert exit_code == 0
            captured = capsys.readouterr()
            # Should show help

    @pytest.mark.asyncio
    async def test_main_install(self):
        """Test install command via main."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            
            def fake_git_clone(*args, **kwargs):
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
                
                return MagicMock(stdout="Cloning...", returncode=0)
            
            with patch('subprocess.run', side_effect=fake_git_clone):
                with patch('sys.argv', [
                    'agent-bus-skills',
                    '--skills-dir', tmpdir,
                    'install',
                    'https://github.com/test/test-skill',
                    '--name', 'test-skill'
                ]):
                    exit_code = main()
                    
                    assert exit_code == 0

    def test_main_list(self):
        """Test list command via main."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('sys.argv', [
                'agent-bus-skills',
                '--skills-dir', tmpdir,
                'list'
            ]):
                exit_code = main()
                
                assert exit_code == 0

    def test_main_info_not_found(self):
        """Test info command for non-existent skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('sys.argv', [
                'agent-bus-skills',
                '--skills-dir', tmpdir,
                'info',
                'nonexistent'
            ]):
                exit_code = main()
                
                assert exit_code == 1
