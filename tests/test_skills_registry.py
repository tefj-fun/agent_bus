"""Tests for skills registry format and loader."""

import pytest
import json
import tempfile
from pathlib import Path
from pydantic import ValidationError

from src.skills import (
    SkillRegistry,
    SkillMetadataSchema,
    SkillsRegistrySchema,
    EXAMPLE_SKILL_METADATA,
)


class TestSkillMetadataSchema:
    """Test JSON schema validation for skill metadata."""

    def test_valid_skill_metadata(self):
        """Test that valid skill metadata passes validation."""
        schema = SkillMetadataSchema(**EXAMPLE_SKILL_METADATA)
        assert schema.name == "ui-ux-pro-max"
        assert schema.version == "1.0.0"
        assert schema.author == "ComposioHQ"

    def test_minimal_skill_metadata(self):
        """Test minimal valid skill metadata."""
        minimal = {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "A test skill",
            "author": "Test Author",
        }
        schema = SkillMetadataSchema(**minimal)
        assert schema.name == "test-skill"
        assert schema.capabilities == []
        assert schema.required_tools == []

    def test_invalid_version_format(self):
        """Test that invalid version format fails validation."""
        invalid = {
            "name": "test-skill",
            "version": "not-a-version",
            "description": "Test",
            "author": "Test",
        }
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadataSchema(**invalid)
        assert "Invalid semver version" in str(exc_info.value)

    def test_invalid_skill_name_uppercase(self):
        """Test that uppercase skill names fail validation."""
        invalid = {
            "name": "Test-Skill",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
        }
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadataSchema(**invalid)
        assert "must be lowercase" in str(exc_info.value)

    def test_invalid_skill_name_special_chars(self):
        """Test that skill names with special chars fail validation."""
        invalid = {
            "name": "test@skill!",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
        }
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadataSchema(**invalid)
        assert "alphanumeric" in str(exc_info.value)

    def test_empty_skill_name(self):
        """Test that empty skill name fails validation."""
        invalid = {"name": "", "version": "1.0.0", "description": "Test", "author": "Test"}
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadataSchema(**invalid)
        assert "cannot be empty" in str(exc_info.value)

    def test_invalid_python_version(self):
        """Test that invalid Python version fails validation."""
        invalid = {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "min_python_version": "not-a-version",
        }
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadataSchema(**invalid)
        assert "Invalid Python version" in str(exc_info.value)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        invalid = {
            "name": "test-skill",
            "version": "1.0.0",
            "description": "Test",
            "author": "Test",
            "unknown_field": "value",
        }
        with pytest.raises(ValidationError) as exc_info:
            SkillMetadataSchema(**invalid)
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestSkillsRegistrySchema:
    """Test registry file schema validation."""

    def test_valid_registry_schema(self):
        """Test valid registry schema."""
        registry = {
            "version": "1.0.0",
            "skills": {
                "test-skill": {
                    "name": "test-skill",
                    "version": "1.0.0",
                    "description": "Test",
                    "author": "Test",
                }
            },
            "updated_at": "2026-02-01T12:00:00Z",
        }
        schema = SkillsRegistrySchema(**registry)
        assert schema.version == "1.0.0"
        assert "test-skill" in schema.skills

    def test_empty_registry(self):
        """Test empty registry is valid."""
        registry = {"version": "1.0.0", "skills": {}}
        schema = SkillsRegistrySchema(**registry)
        assert schema.skills == {}


class TestSkillRegistry:
    """Test SkillRegistry class."""

    def test_registry_initialization(self):
        """Test registry initialization creates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = SkillRegistry(tmpdir)
            assert Path(tmpdir).exists()
            assert registry.list_skills() == []

    def test_load_skill_with_valid_metadata(self):
        """Test loading skill with valid skill.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skill directory with skill.json
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()

            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "A test skill",
                "author": "Test Author",
                "capabilities": [{"name": "testing", "description": "Testing capability"}],
                "required_tools": [{"name": "shell", "required": True}],
                "tags": ["test"],
            }

            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)

            # Create entry point
            with open(skill_dir / "skill.md", "w") as f:
                f.write("# Test Skill")

            # Load registry
            registry = SkillRegistry(tmpdir)

            # Verify skill loaded
            assert registry.has_skill("test-skill")
            skill = registry.get_skill("test-skill")
            assert skill.name == "test-skill"
            assert skill.version == "1.0.0"
            assert skill.author == "Test Author"
            assert "testing" in skill.capabilities
            assert "shell" in skill.required_tools
            assert "test" in skill.tags

    def test_load_skill_without_metadata(self):
        """Test loading skill without skill.json (fallback)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skill directory without skill.json
            skill_dir = Path(tmpdir) / "fallback-skill"
            skill_dir.mkdir()

            with open(skill_dir / "README.md", "w") as f:
                f.write("# Fallback Skill")

            # Load registry
            registry = SkillRegistry(tmpdir)

            # Verify skill loaded with defaults
            assert registry.has_skill("fallback-skill")
            skill = registry.get_skill("fallback-skill")
            assert skill.name == "fallback-skill"
            assert skill.version == "0.1.0"
            assert skill.author == "Unknown"

    def test_load_skill_with_invalid_json(self):
        """Test that invalid JSON is handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "invalid-skill"
            skill_dir.mkdir()

            # Write invalid JSON
            with open(skill_dir / "skill.json", "w") as f:
                f.write("{invalid json")

            # Registry should load but skip this skill
            registry = SkillRegistry(tmpdir)
            assert not registry.has_skill("invalid-skill")

    def test_load_skill_with_invalid_schema(self):
        """Test that invalid schema is handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "invalid-schema"
            skill_dir.mkdir()

            # Write JSON with invalid schema
            invalid = {
                "name": "Invalid@Name",
                "version": "not-a-version",
                "description": "Test",
                "author": "Test",
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(invalid, f)

            # Registry should load but skip this skill
            registry = SkillRegistry(tmpdir)
            assert not registry.has_skill("invalid-schema")

    def test_skill_name_mismatch_warning(self):
        """Test that name mismatch uses directory name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "correct-name"
            skill_dir.mkdir()

            # skill.json has different name
            skill_json = {
                "name": "wrong-name",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test",
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)

            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")

            registry = SkillRegistry(tmpdir)

            # Should use directory name
            assert registry.has_skill("correct-name")
            skill = registry.get_skill("correct-name")
            assert skill.name == "correct-name"

    def test_reload_registry(self):
        """Test reloading registry picks up new skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = SkillRegistry(tmpdir)
            assert len(registry.list_skills()) == 0

            # Add a new skill
            skill_dir = Path(tmpdir) / "new-skill"
            skill_dir.mkdir()
            skill_json = {
                "name": "new-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test",
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")

            # Reload
            registry.reload()

            assert registry.has_skill("new-skill")

    def test_save_registry(self):
        """Test saving registry to skills.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skill
            skill_dir = Path(tmpdir) / "test-skill"
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

            registry = SkillRegistry(tmpdir)
            registry.save_registry()

            # Verify skills.json was created
            registry_file = Path(tmpdir) / "skills.json"
            assert registry_file.exists()

            # Verify content
            with open(registry_file) as f:
                data = json.load(f)

            assert data["version"] == "1.0.0"
            assert "test-skill" in data["skills"]
            assert "updated_at" in data

    def test_get_skills_by_capability(self):
        """Test filtering skills by capability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skill with testing capability
            skill_dir = Path(tmpdir) / "test-skill"
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

            registry = SkillRegistry(tmpdir)

            skills = registry.get_skills_by_capability("testing")
            assert len(skills) == 1
            assert skills[0].name == "test-skill"

    def test_get_skills_by_tag(self):
        """Test filtering skills by tag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skill with tag
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()
            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test",
                "tags": ["testing", "automation"],
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")

            registry = SkillRegistry(tmpdir)

            skills = registry.get_skills_by_tag("testing")
            assert len(skills) == 1
            assert skills[0].name == "test-skill"

    def test_validate_skill_directory_valid(self):
        """Test validating a valid skill directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
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

            registry = SkillRegistry(tmpdir)
            is_valid, error = registry.validate_skill_directory(skill_dir)

            assert is_valid
            assert error is None

    def test_validate_skill_directory_no_entry_point(self):
        """Test validating skill without entry point."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()

            skill_json = {
                "name": "test-skill",
                "version": "1.0.0",
                "description": "Test",
                "author": "Test",
            }
            with open(skill_dir / "skill.json", "w") as f:
                json.dump(skill_json, f)

            registry = SkillRegistry(tmpdir)
            is_valid, error = registry.validate_skill_directory(skill_dir)

            assert not is_valid
            assert "No entry point file found" in error

    def test_validate_skill_directory_invalid_json(self):
        """Test validating skill with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "test-skill"
            skill_dir.mkdir()

            with open(skill_dir / "skill.json", "w") as f:
                f.write("{invalid}")
            with open(skill_dir / "skill.md", "w") as f:
                f.write("Test")

            registry = SkillRegistry(tmpdir)
            is_valid, error = registry.validate_skill_directory(skill_dir)

            assert not is_valid
            assert "Invalid skill.json" in error

    def test_skip_hidden_directories(self):
        """Test that hidden directories are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create hidden directory
            hidden_dir = Path(tmpdir) / ".hidden"
            hidden_dir.mkdir()

            registry = SkillRegistry(tmpdir)
            assert not registry.has_skill(".hidden")

    def test_skip_pycache(self):
        """Test that __pycache__ is skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "__pycache__"
            cache_dir.mkdir()

            registry = SkillRegistry(tmpdir)
            assert not registry.has_skill("__pycache__")
