"""Skills manager for loading and executing Claude Skills."""

import os
import subprocess
from typing import Dict, Optional, Any, List
from pathlib import Path
import logging
import asyncpg

from .registry import (
    SkillRegistry,
    SkillMetadata,
    SkillRegistryError,
    SkillValidationError,
    SkillNotFoundError,
)
from .allowlist import SkillAllowlistManager, SkillPermissionError

logger = logging.getLogger(__name__)


class SkillLoadError(Exception):
    """Failed to load skill content."""
    pass


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
    """
    Manages loading and execution of Claude Skills.
    
    Features:
    - Skill discovery and validation via SkillRegistry
    - Lazy loading of skill content
    - Content caching
    - Git-based skill installation
    - Per-agent skill permission enforcement
    - Capability-based skill discovery
    - Comprehensive error handling
    """

    def __init__(
        self,
        skills_dir: str = "./skills",
        db_pool: Optional[asyncpg.Pool] = None
    ):
        self.skills_dir = Path(skills_dir)
        self.loaded_skills: Dict[str, Skill] = {}
        self.registry = SkillRegistry(str(skills_dir))
        self.db_pool = db_pool
        self.allowlist_manager = SkillAllowlistManager(db_pool) if db_pool else None

    async def load_skill(
        self,
        skill_name: str,
        agent_id: Optional[str] = None,
        enforce_permissions: bool = True
    ) -> Optional[Skill]:
        """
        Load a skill from the local directory with optional permission check.

        Args:
            skill_name: Name of the skill to load
            agent_id: Agent requesting the skill (for permission check)
            enforce_permissions: Whether to enforce permission checks

        Returns:
            Loaded Skill object or None if not found
            
        Raises:
            SkillNotFoundError: If skill is not in registry
            SkillLoadError: If skill content cannot be loaded
            SkillPermissionError: If agent lacks permission to use skill
        """
        # Check permissions if agent_id provided and allowlist available
        if enforce_permissions and agent_id and self.allowlist_manager:
            await self.allowlist_manager.enforce_permission(agent_id, skill_name)
        
        # Check cache first
        if skill_name in self.loaded_skills:
            logger.debug(f"Returning cached skill: {skill_name}")
            return self.loaded_skills[skill_name]

        # Get metadata from registry
        metadata = self.registry.get_skill(skill_name)
        if not metadata:
            logger.error(f"Skill '{skill_name}' not found in registry")
            raise SkillNotFoundError(f"Skill '{skill_name}' not found in registry")

        # Load skill content
        try:
            content = self._load_skill_content(metadata)
        except Exception as e:
            logger.error(f"Failed to load content for skill '{skill_name}': {e}")
            raise SkillLoadError(f"Cannot load skill content: {e}")

        # Create and cache skill
        skill = Skill(metadata, content)
        self.loaded_skills[skill_name] = skill
        logger.info(f"Loaded skill: {skill_name} v{metadata.version}")

        return skill

    def _load_skill_content(self, metadata: SkillMetadata) -> str:
        """
        Load skill prompt content from filesystem.
        
        Args:
            metadata: SkillMetadata containing path and entry_point
            
        Returns:
            Skill prompt content as string
            
        Raises:
            SkillLoadError: If content cannot be loaded
        """
        skill_path = Path(metadata.path)

        # Determine entry point file
        if metadata.entry_point:
            prompt_files = [metadata.entry_point]
        else:
            # Default priority order
            prompt_files = ["skill.md", "README.md", "prompt.md"]

        # Try each potential entry point
        for prompt_file in prompt_files:
            prompt_path = skill_path / prompt_file
            if prompt_path.exists():
                try:
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    if not content.strip():
                        logger.warning(
                            f"Empty content in {prompt_file} for skill '{metadata.name}'"
                        )
                        continue
                    
                    logger.debug(
                        f"Loaded content from {prompt_file} for skill '{metadata.name}'"
                    )
                    return content
                    
                except Exception as e:
                    logger.error(
                        f"Failed to read {prompt_file} for skill '{metadata.name}': {e}"
                    )
                    continue

        # No valid content found
        raise SkillLoadError(
            f"No readable prompt content found for skill '{metadata.name}'. "
            f"Tried: {', '.join(prompt_files)}"
        )

    async def install_skill(self, git_url: str, skill_name: str) -> bool:
        """
        Clone a skill from GitHub to the local directory.

        Args:
            git_url: GitHub repository URL
            skill_name: Name to use for the skill directory

        Returns:
            True if successful, False otherwise
            
        Raises:
            SkillRegistryError: If installation fails
        """
        target_path = self.skills_dir / skill_name

        if target_path.exists():
            logger.error(f"Skill directory '{skill_name}' already exists")
            raise SkillRegistryError(f"Skill directory '{skill_name}' already exists")

        try:
            logger.info(f"Installing skill '{skill_name}' from {git_url}")
            
            result = subprocess.run(
                ["git", "clone", git_url, str(target_path)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            logger.debug(f"Git clone output: {result.stdout}")
            
            # Validate the cloned skill
            is_valid, error = self.registry.validate_skill_directory(target_path)
            if not is_valid:
                logger.error(f"Cloned skill is invalid: {error}")
                # Clean up invalid clone
                subprocess.run(["rm", "-rf", str(target_path)], check=False)
                raise SkillRegistryError(f"Invalid skill: {error}")
            
            # Reload registry to pick up new skill
            self.registry.reload()
            
            # Save updated registry
            self.registry.save_registry()
            
            logger.info(f"Successfully installed skill '{skill_name}'")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Git clone timed out for {git_url}")
            raise SkillRegistryError("Git clone operation timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e.stderr}")
            raise SkillRegistryError(f"Git clone failed: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error installing skill: {e}")
            raise SkillRegistryError(f"Installation failed: {e}")

    async def update_skill(self, skill_name: str) -> bool:
        """
        Update a skill from its git repository.

        Args:
            skill_name: Name of the skill to update

        Returns:
            True if successful
            
        Raises:
            SkillNotFoundError: If skill is not found
            SkillRegistryError: If update fails
        """
        skill_path = self.registry.get_skill_path(skill_name)
        if not skill_path:
            logger.error(f"Skill '{skill_name}' not found")
            raise SkillNotFoundError(f"Skill '{skill_name}' not found")

        try:
            logger.info(f"Updating skill '{skill_name}'")
            
            result = subprocess.run(
                ["git", "-C", skill_path, "pull"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            logger.debug(f"Git pull output: {result.stdout}")
            
            # Clear cache for this skill
            if skill_name in self.loaded_skills:
                del self.loaded_skills[skill_name]
            
            # Reload registry
            self.registry.reload()
            
            # Save updated registry
            self.registry.save_registry()
            
            logger.info(f"Successfully updated skill '{skill_name}'")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Git pull timed out for '{skill_name}'")
            raise SkillRegistryError("Git pull operation timed out")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git pull failed for '{skill_name}': {e.stderr}")
            raise SkillRegistryError(f"Git pull failed: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error updating skill '{skill_name}': {e}")
            raise SkillRegistryError(f"Update failed: {e}")

    def list_skills(self) -> list[SkillMetadata]:
        """
        List all available skills.
        
        Returns:
            List of SkillMetadata objects
        """
        return self.registry.list_skills()

    def get_skill_info(self, skill_name: str) -> Optional[SkillMetadata]:
        """
        Get information about a skill.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            SkillMetadata or None if not found
        """
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
            Skill prompt with context
            
        Raises:
            SkillNotFoundError: If skill is not found
            SkillLoadError: If skill cannot be loaded
        """
        skill = await self.load_skill(skill_name)
        
        # For now, return the skill prompt
        # The agent will use this prompt when calling Claude
        # Future: could apply context templating here
        return skill.get_prompt()

    def reload_registry(self) -> None:
        """Reload the skills registry from disk."""
        logger.info("Reloading skills registry")
        self.registry.reload()
        # Clear cache since skills may have changed
        self.loaded_skills.clear()

    def get_skills_by_capability(self, capability: str) -> list[SkillMetadata]:
        """
        Find skills that provide a specific capability.
        
        Args:
            capability: Capability name to search for
            
        Returns:
            List of matching skills
        """
        return self.registry.get_skills_by_capability(capability)

    def get_skills_by_tag(self, tag: str) -> list[SkillMetadata]:
        """
        Find skills with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of matching skills
        """
        return self.registry.get_skills_by_tag(tag)
    
    async def find_skills_for_capability(
        self,
        capability: str,
        agent_id: Optional[str] = None
    ) -> List[str]:
        """
        Find skills that provide a capability, filtered by agent permissions.
        
        This uses the capability mapping table and agent allowlist.
        
        Args:
            capability: Capability name (e.g., 'ui-design')
            agent_id: Optional agent ID to filter by permissions
            
        Returns:
            List of skill names, ordered by priority
        """
        if not self.allowlist_manager:
            # Fallback to registry-based capability search
            logger.warning(
                "Allowlist manager not available, using registry-only capability search"
            )
            skills = self.registry.get_skills_by_capability(capability)
            return [s.name for s in skills]
        
        return await self.allowlist_manager.get_skills_by_capability(
            capability,
            agent_id=agent_id
        )
    
    async def get_allowed_skills(self, agent_id: str) -> List[str]:
        """
        Get list of skills explicitly allowed for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            List of allowed skill names (empty if using default allow-all)
        """
        if not self.allowlist_manager:
            logger.warning("Allowlist manager not available")
            return []
        
        return await self.allowlist_manager.get_agent_allowed_skills(agent_id)
    
    async def check_skill_permission(
        self,
        agent_id: str,
        skill_name: str
    ) -> bool:
        """
        Check if an agent has permission to use a skill.
        
        Args:
            agent_id: Agent identifier
            skill_name: Skill name
            
        Returns:
            True if permitted, False otherwise (or if allowlist not available)
        """
        if not self.allowlist_manager:
            # Backward compatibility: allow all if no allowlist
            return True
        
        return await self.allowlist_manager.check_permission(agent_id, skill_name)
