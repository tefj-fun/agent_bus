"""Tests for skills API endpoints."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.main import app
from src.api.routes.skills import skills_manager


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_skills_dir():
    """Create temporary skills directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Patch skills manager to use temp dir
        skills_manager.skills_dir = Path(tmpdir)
        skills_manager.registry.skills_dir = Path(tmpdir)
        skills_manager.registry._registry.clear()
        skills_manager.loaded_skills.clear()
        yield tmpdir


class TestSkillsAPI:
    """Test skills API endpoints."""

    def test_list_skills_empty(self, client, temp_skills_dir):
        """Test listing skills when none are installed."""
        skills_manager.reload_registry()

        response = client.get("/api/skills")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["skills"] == []

    def test_list_skills(self, client, temp_skills_dir):
        """Test listing installed skills."""
        # Create test skill
        skill_dir = Path(temp_skills_dir) / "test-skill"
        skill_dir.mkdir()

        skill_json = {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "Test skill",
            "author": "Test Author",
        }
        with open(skill_dir / "skill.json", "w") as f:
            json.dump(skill_json, f)
        with open(skill_dir / "skill.md", "w") as f:
            f.write("# Test Skill")

        skills_manager.reload_registry()

        response = client.get("/api/skills")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["skills"]) == 1
        assert data["skills"][0]["name"] == "test-skill"
        assert data["skills"][0]["version"] == "1.0.0"

    def test_list_skills_by_capability(self, client, temp_skills_dir):
        """Test filtering skills by capability."""
        # Create test skill with capability
        skill_dir = Path(temp_skills_dir) / "test-skill"
        skill_dir.mkdir()

        skill_json = {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "capabilities": [{"name": "testing"}],
        }
        with open(skill_dir / "skill.json", "w") as f:
            json.dump(skill_json, f)
        with open(skill_dir / "skill.md", "w") as f:
            f.write("Test")

        skills_manager.reload_registry()

        response = client.get("/api/skills?capability=testing")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "testing" in data["skills"][0]["capabilities"]

    def test_list_skills_by_tag(self, client, temp_skills_dir):
        """Test filtering skills by tag."""
        skill_dir = Path(temp_skills_dir) / "test-skill"
        skill_dir.mkdir()

        skill_json = {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "tags": ["automation"],
        }
        with open(skill_dir / "skill.json", "w") as f:
            json.dump(skill_json, f)
        with open(skill_dir / "skill.md", "w") as f:
            f.write("Test")

        skills_manager.reload_registry()

        response = client.get("/api/skills?tag=automation")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "automation" in data["skills"][0]["tags"]

    def test_get_skill_success(self, client, temp_skills_dir):
        """Test getting a specific skill."""
        skill_dir = Path(temp_skills_dir) / "test-skill"
        skill_dir.mkdir()

        skill_json = {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "Test skill",
            "author": "Test Author",
            "repository": "https://github.com/test/skill",
            "license": "MIT",
        }
        with open(skill_dir / "skill.json", "w") as f:
            json.dump(skill_json, f)
        with open(skill_dir / "skill.md", "w") as f:
            f.write("Test")

        skills_manager.reload_registry()

        response = client.get("/api/skills/test-skill")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-skill"
        assert data["version"] == "1.0.0"
        assert data["description"] == "Test skill"
        assert data["author"] == "Test Author"
        assert data["repository"] == "https://github.com/test/skill"
        assert data["license"] == "MIT"

    def test_get_skill_not_found(self, client, temp_skills_dir):
        """Test getting non-existent skill."""
        skills_manager.reload_registry()

        response = client.get("/api/skills/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_install_skill_success(self, client, temp_skills_dir):
        """Test successful skill installation."""
        skill_dir = Path(temp_skills_dir) / "new-skill"

        def fake_git_clone(*args, **kwargs):
            skill_dir.mkdir()

            skill_json = {
                "name": "new-skill",
                "version": "1.0.0",
                "description": "New skill",
                "author": "Test",
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("# New Skill")

            return MagicMock(stdout="Cloning...", returncode=0)

        with patch("subprocess.run", side_effect=fake_git_clone):
            response = client.post(
                "/api/skills/install",
                json={"git_url": "https://github.com/test/new-skill", "skill_name": "new-skill"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "new-skill"
            assert data["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_install_skill_auto_name(self, client, temp_skills_dir):
        """Test installation with auto-extracted name."""
        skill_dir = Path(temp_skills_dir) / "auto-skill"

        def fake_git_clone(*args, **kwargs):
            skill_dir.mkdir()

            skill_json = {
                "name": "auto-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test",
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")

            return MagicMock(stdout="Cloning...", returncode=0)

        with patch("subprocess.run", side_effect=fake_git_clone):
            response = client.post(
                "/api/skills/install", json={"git_url": "https://github.com/test/auto-skill.git"}
            )

            assert response.status_code == 201

    def test_install_skill_already_exists(self, client, temp_skills_dir):
        """Test installing skill that already exists."""
        # Create existing skill
        skill_dir = Path(temp_skills_dir) / "existing-skill"
        skill_dir.mkdir()

        skills_manager.reload_registry()

        response = client.post(
            "/api/skills/install",
            json={"git_url": "https://github.com/test/skill", "skill_name": "existing-skill"},
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_install_skill_git_failure(self, client, temp_skills_dir):
        """Test handling git clone failure."""
        from subprocess import CalledProcessError

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = CalledProcessError(1, "git", stderr="Clone failed")

            response = client.post(
                "/api/skills/install",
                json={"git_url": "https://github.com/test/skill", "skill_name": "new-skill"},
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_skill_success(self, client, temp_skills_dir):
        """Test successful skill update."""
        # Create existing skill
        skill_dir = Path(temp_skills_dir) / "test-skill"
        skill_dir.mkdir()

        skill_json = {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
        }
        with open(skill_dir / "skill.json", "w") as f:
            json.dump(skill_json, f)
        with open(skill_dir / "skill.md", "w") as f:
            f.write("Test")

        skills_manager.reload_registry()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Already up to date.", returncode=0)

            response = client.post("/api/skills/test-skill/update")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "updated successfully" in data["message"]

    def test_update_skill_not_found(self, client, temp_skills_dir):
        """Test updating non-existent skill."""
        skills_manager.reload_registry()

        response = client.post("/api/skills/nonexistent/update")

        assert response.status_code == 404

    def test_reload_registry(self, client, temp_skills_dir):
        """Test reloading registry."""
        response = client.post("/api/skills/reload")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "reloaded" in data["message"]

    def test_skill_response_complete(self, client, temp_skills_dir):
        """Test that skill response includes all fields."""
        skill_dir = Path(temp_skills_dir) / "test-skill"
        skill_dir.mkdir()

        skill_json = {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "Test skill",
            "author": "Test Author",
            "capabilities": [{"name": "testing"}],
            "required_tools": [{"name": "browser", "required": True}],
            "entry_point": "skill.md",
            "repository": "https://github.com/test/skill",
            "license": "MIT",
            "tags": ["test"],
            "dependencies": [{"name": "requests", "version": ">=2.0.0"}],
            "min_python_version": "3.10",
        }
        with open(skill_dir / "skill.json", "w") as f:
            json.dump(skill_json, f)
        with open(skill_dir / "skill.md", "w") as f:
            f.write("Test")

        skills_manager.reload_registry()

        response = client.get("/api/skills/test-skill")

        assert response.status_code == 200
        data = response.json()

        # Verify all fields are present
        assert data["name"] == "test-skill"
        assert data["version"] == "1.0.0"
        assert data["description"] == "Test skill"
        assert data["author"] == "Test Author"
        assert "testing" in data["capabilities"]
        assert "browser" in data["required_tools"]
        assert data["entry_point"] == "skill.md"
        assert data["repository"] == "https://github.com/test/skill"
        assert data["license"] == "MIT"
        assert "test" in data["tags"]
        assert len(data["dependencies"]) == 1
        assert data["min_python_version"] == "3.10"
        assert "path" in data
