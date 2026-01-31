"""Skills registry for managing available Claude Skills."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import json
import os


@dataclass
class SkillMetadata:
    """Metadata for a Claude Skill."""

    name: str
    version: str
    description: str
    author: str
    capabilities: List[str]
    required_tools: List[str]
    path: str


class SkillRegistry:
    """Registry for tracking and discovering Claude Skills."""

    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = skills_dir
        self._registry: Dict[str, SkillMetadata] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load all available skills from the skills directory."""
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir, exist_ok=True)
            return

        for skill_name in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, skill_name)

            if not os.path.isdir(skill_path):
                continue

            # Look for skill.json or README.md for metadata
            metadata_path = os.path.join(skill_path, "skill.json")

            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    data = json.load(f)
                    self._registry[skill_name] = SkillMetadata(
                        name=data.get("name", skill_name),
                        version=data.get("version", "0.1.0"),
                        description=data.get("description", ""),
                        author=data.get("author", "Unknown"),
                        capabilities=data.get("capabilities", []),
                        required_tools=data.get("required_tools", []),
                        path=skill_path,
                    )
            else:
                # Basic metadata from directory name
                self._registry[skill_name] = SkillMetadata(
                    name=skill_name,
                    version="0.1.0",
                    description=f"Skill: {skill_name}",
                    author="Unknown",
                    capabilities=[],
                    required_tools=[],
                    path=skill_path,
                )

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """Get skill metadata by name."""
        return self._registry.get(name)

    def list_skills(self) -> List[SkillMetadata]:
        """List all available skills."""
        return list(self._registry.values())

    def has_skill(self, name: str) -> bool:
        """Check if a skill is registered."""
        return name in self._registry

    def get_skill_path(self, name: str) -> Optional[str]:
        """Get the filesystem path for a skill."""
        skill = self.get_skill(name)
        return skill.path if skill else None

    def reload(self) -> None:
        """Reload the registry from disk."""
        self._registry.clear()
        self._load_registry()
