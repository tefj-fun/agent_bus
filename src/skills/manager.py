"""Skills manager for loading and executing Claude Skills."""

import os
import subprocess
from typing import Dict, Optional, Any
from pathlib import Path

from .registry import SkillRegistry, SkillMetadata


class Skill:
    """Represents a loaded Claude Skill."""

    def __init__(self, metadata: SkillMetadata, content: str):
        self.metadata = metadata
        self.content = content
        self.name = metadata.name
        self.version = metadata.version

    def get_prompt(self) -> str:
        """Get the skill prompt content."""
        return self.content

    def get_capabilities(self) -> list[str]:
        """Get skill capabilities."""
        return self.metadata.capabilities


class SkillsManager:
    """Manages loading and execution of Claude Skills."""

    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = skills_dir
        self.loaded_skills: Dict[str, Skill] = {}
        self.registry = SkillRegistry(skills_dir)

    async def load_skill(self, skill_name: str) -> Optional[Skill]:
        """
        Load a skill from the local directory.

        Args:
            skill_name: Name of the skill to load

        Returns:
            Loaded Skill object or None if not found
        """
        # Check cache first
        if skill_name in self.loaded_skills:
            return self.loaded_skills[skill_name]

        # Get metadata from registry
        metadata = self.registry.get_skill(skill_name)
        if not metadata:
            print(f"Skill '{skill_name}' not found in registry")
            return None

        # Load skill content
        skill_path = Path(metadata.path)

        # Look for skill.md or README.md as the main prompt
        prompt_files = ["skill.md", "README.md", "prompt.md"]
        content = None

        for prompt_file in prompt_files:
            prompt_path = skill_path / prompt_file
            if prompt_path.exists():
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read()
                break

        if content is None:
            print(f"No prompt content found for skill '{skill_name}'")
            return None

        # Create and cache skill
        skill = Skill(metadata, content)
        self.loaded_skills[skill_name] = skill

        return skill

    async def install_skill(self, git_url: str, skill_name: str) -> bool:
        """
        Clone a skill from GitHub to the local directory.

        Args:
            git_url: GitHub repository URL
            skill_name: Name to use for the skill directory

        Returns:
            True if successful, False otherwise
        """
        target_path = os.path.join(self.skills_dir, skill_name)

        if os.path.exists(target_path):
            print(f"Skill directory '{skill_name}' already exists")
            return False

        try:
            subprocess.run(
                ["git", "clone", git_url, target_path],
                check=True,
                capture_output=True,
                text=True
            )
            # Reload registry to pick up new skill
            self.registry.reload()
            print(f"Successfully installed skill '{skill_name}'")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install skill: {e.stderr}")
            return False

    async def update_skill(self, skill_name: str) -> bool:
        """
        Update a skill from its git repository.

        Args:
            skill_name: Name of the skill to update

        Returns:
            True if successful, False otherwise
        """
        skill_path = self.registry.get_skill_path(skill_name)
        if not skill_path:
            print(f"Skill '{skill_name}' not found")
            return False

        try:
            subprocess.run(
                ["git", "-C", skill_path, "pull"],
                check=True,
                capture_output=True,
                text=True
            )
            # Clear cache for this skill
            if skill_name in self.loaded_skills:
                del self.loaded_skills[skill_name]
            # Reload registry
            self.registry.reload()
            print(f"Successfully updated skill '{skill_name}'")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to update skill: {e.stderr}")
            return False

    def list_skills(self) -> list[SkillMetadata]:
        """List all available skills."""
        return self.registry.list_skills()

    def get_skill_info(self, skill_name: str) -> Optional[SkillMetadata]:
        """Get information about a skill."""
        return self.registry.get_skill(skill_name)

    async def execute_skill(
        self,
        skill_name: str,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Execute a skill with given context.

        This method returns the skill's prompt that should be
        passed to the LLM along with the context.

        Args:
            skill_name: Name of the skill to execute
            context: Context data for the skill

        Returns:
            Skill prompt with context or None if skill not found
        """
        skill = await self.load_skill(skill_name)
        if not skill:
            return None

        # For now, return the skill prompt
        # The agent will use this prompt when calling Claude
        return skill.get_prompt()
