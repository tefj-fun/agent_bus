"""Skills registry for managing available Claude Skills."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import logging
from datetime import datetime

from pydantic import ValidationError

from .schema import SkillMetadataSchema, SkillsRegistrySchema

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Metadata for a Claude Skill."""

    name: str
    version: str
    description: str
    author: str
    capabilities: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    path: str = ""
    entry_point: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[Dict[str, Any]] = field(default_factory=list)
    min_python_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_schema(cls, schema: SkillMetadataSchema, path: str) -> "SkillMetadata":
        """Create SkillMetadata from validated schema."""
        return cls(
            name=schema.name,
            version=schema.version,
            description=schema.description,
            author=schema.author,
            capabilities=[cap.name for cap in schema.capabilities],
            required_tools=[tool.name for tool in schema.required_tools if tool.required],
            path=path,
            entry_point=schema.entry_point,
            repository=schema.repository,
            license=schema.license,
            tags=schema.tags,
            dependencies=[dep.model_dump() for dep in schema.dependencies],
            min_python_version=schema.min_python_version,
            metadata=schema.metadata,
        )


class SkillRegistryError(Exception):
    """Base exception for skill registry errors."""

    pass


class SkillValidationError(SkillRegistryError):
    """Skill validation failed."""

    pass


class SkillNotFoundError(SkillRegistryError):
    """Skill not found in registry."""

    pass


class SkillRegistry:
    """
    Registry for tracking and discovering Claude Skills.

    Features:
    - Automatic skill discovery from skills directory
    - JSON schema validation for skill.json files
    - Robust error handling and logging
    - Version compatibility checks
    - Registry persistence to skills.json
    """

    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = Path(skills_dir)
        self._registry: Dict[str, SkillMetadata] = {}
        self._registry_file = self.skills_dir / "skills.json"
        self._ensure_skills_dir()
        self._load_registry()

    def _ensure_skills_dir(self) -> None:
        """Ensure skills directory exists."""
        try:
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Skills directory ensured at: {self.skills_dir}")
        except Exception as e:
            logger.error(f"Failed to create skills directory: {e}")
            raise SkillRegistryError(f"Cannot create skills directory: {e}")

    def _load_registry(self) -> None:
        """
        Load all available skills from the skills directory.

        This method:
        1. Scans the skills directory for subdirectories
        2. Validates skill.json against schema
        3. Falls back to basic metadata if skill.json is missing/invalid
        4. Logs errors but continues loading other skills
        """
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory does not exist: {self.skills_dir}")
            return

        logger.info(f"Loading skills from: {self.skills_dir}")
        loaded_count = 0
        error_count = 0

        for item in self.skills_dir.iterdir():
            if not item.is_dir():
                continue

            skill_name = item.name

            # Skip special directories
            if skill_name.startswith(".") or skill_name == "__pycache__":
                continue

            try:
                metadata = self._load_skill_metadata(skill_name, item)
                self._registry[skill_name] = metadata
                loaded_count += 1
                logger.debug(f"Loaded skill: {skill_name} v{metadata.version}")
            except SkillValidationError as e:
                logger.error(f"Validation failed for skill '{skill_name}': {e}")
                error_count += 1
            except Exception as e:
                logger.error(f"Unexpected error loading skill '{skill_name}': {e}")
                error_count += 1

        logger.info(f"Registry loaded: {loaded_count} skills, {error_count} errors")

    def _load_skill_metadata(self, skill_name: str, skill_path: Path) -> SkillMetadata:
        """
        Load and validate metadata for a single skill.

        Args:
            skill_name: Name of the skill directory
            skill_path: Path to skill directory

        Returns:
            SkillMetadata object

        Raises:
            SkillValidationError: If validation fails
        """
        metadata_path = skill_path / "skill.json"

        if metadata_path.exists():
            # Load and validate skill.json
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Validate against schema
                schema = SkillMetadataSchema(**data)

                # Verify skill name matches directory name
                if schema.name != skill_name:
                    logger.warning(
                        f"Skill name mismatch: directory='{skill_name}', "
                        f"skill.json='{schema.name}'. Using directory name."
                    )
                    # Override with directory name for consistency
                    schema.name = skill_name

                return SkillMetadata.from_schema(schema, str(skill_path))

            except json.JSONDecodeError as e:
                raise SkillValidationError(f"Invalid JSON in skill.json: {e}")
            except ValidationError as e:
                raise SkillValidationError(f"Schema validation failed: {e}")
            except Exception as e:
                raise SkillValidationError(f"Failed to load skill.json: {e}")
        else:
            # Fallback to basic metadata from directory
            logger.debug(f"No skill.json found for '{skill_name}', using basic metadata")
            return SkillMetadata(
                name=skill_name,
                version="0.1.0",
                description=f"Skill: {skill_name}",
                author="Unknown",
                capabilities=[],
                required_tools=[],
                path=str(skill_path),
            )

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """
        Get skill metadata by name.

        Args:
            name: Skill name

        Returns:
            SkillMetadata or None if not found
        """
        return self._registry.get(name)

    def list_skills(self) -> List[SkillMetadata]:
        """
        List all available skills.

        Returns:
            List of SkillMetadata objects
        """
        return list(self._registry.values())

    def has_skill(self, name: str) -> bool:
        """
        Check if a skill is registered.

        Args:
            name: Skill name

        Returns:
            True if skill exists
        """
        return name in self._registry

    def get_skill_path(self, name: str) -> Optional[str]:
        """
        Get the filesystem path for a skill.

        Args:
            name: Skill name

        Returns:
            Path string or None if not found
        """
        skill = self.get_skill(name)
        return skill.path if skill else None

    def reload(self) -> None:
        """
        Reload the registry from disk.

        This clears the in-memory registry and re-scans the skills directory.
        """
        logger.info("Reloading skills registry")
        self._registry.clear()
        self._load_registry()

    def register_skill(self, name: str, metadata: SkillMetadata) -> None:
        """
        Manually register a skill.

        Args:
            name: Skill name
            metadata: SkillMetadata object
        """
        self._registry[name] = metadata
        logger.info(f"Registered skill: {name} v{metadata.version}")

    def unregister_skill(self, name: str) -> bool:
        """
        Unregister a skill from the registry.

        Args:
            name: Skill name

        Returns:
            True if skill was removed, False if not found
        """
        if name in self._registry:
            del self._registry[name]
            logger.info(f"Unregistered skill: {name}")
            return True
        return False

    def save_registry(self) -> None:
        """
        Persist the current registry to skills.json.

        This creates a snapshot of all registered skills.
        """
        try:
            registry_data = {
                "version": "1.0.0",
                "updated_at": datetime.utcnow().isoformat() + "Z",
                "skills": {
                    name: {
                        "name": meta.name,
                        "version": meta.version,
                        "description": meta.description,
                        "author": meta.author,
                        "capabilities": meta.capabilities,
                        "required_tools": meta.required_tools,
                        "path": meta.path,
                        "entry_point": meta.entry_point,
                        "repository": meta.repository,
                        "license": meta.license,
                        "tags": meta.tags,
                        "dependencies": meta.dependencies,
                        "min_python_version": meta.min_python_version,
                        "metadata": meta.metadata,
                    }
                    for name, meta in self._registry.items()
                },
            }

            # Validate against schema
            SkillsRegistrySchema(**registry_data)

            # Write to file
            with open(self._registry_file, "w", encoding="utf-8") as f:
                json.dump(registry_data, f, indent=2, sort_keys=True)

            logger.info(f"Registry saved to {self._registry_file}")

        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
            raise SkillRegistryError(f"Cannot save registry: {e}")

    def get_skills_by_capability(self, capability: str) -> List[SkillMetadata]:
        """
        Find skills that provide a specific capability.

        Args:
            capability: Capability name to search for

        Returns:
            List of matching skills
        """
        return [skill for skill in self._registry.values() if capability in skill.capabilities]

    def get_skills_by_tag(self, tag: str) -> List[SkillMetadata]:
        """
        Find skills with a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of matching skills
        """
        return [skill for skill in self._registry.values() if tag in skill.tags]

    def validate_skill_directory(self, skill_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate a skill directory structure.

        Args:
            skill_path: Path to skill directory

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not skill_path.exists():
            return False, f"Directory does not exist: {skill_path}"

        if not skill_path.is_dir():
            return False, f"Not a directory: {skill_path}"

        # Check for skill.json
        skill_json = skill_path / "skill.json"
        if skill_json.exists():
            try:
                with open(skill_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                SkillMetadataSchema(**data)
            except Exception as e:
                return False, f"Invalid skill.json: {e}"

        # Check for entry point files
        entry_points = ["skill.md", "README.md", "prompt.md"]
        has_entry_point = any((skill_path / ep).exists() for ep in entry_points)

        if not has_entry_point:
            return False, "No entry point file found (skill.md, README.md, or prompt.md)"

        return True, None
