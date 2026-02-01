"""Configuration loader for skill allowlists and capability mappings."""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List
import asyncpg

from .allowlist import SkillAllowlistManager

logger = logging.getLogger(__name__)


class AllowlistConfigLoader:
    """Load skill allowlist configuration from YAML files."""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.allowlist_manager = SkillAllowlistManager(db_pool)

    async def load_from_yaml(
        self, config_path: str, clear_existing: bool = False
    ) -> Dict[str, int]:
        """
        Load allowlist and capability mappings from YAML file.

        Args:
            config_path: Path to YAML configuration file
            clear_existing: Whether to clear existing entries before loading

        Returns:
            Dictionary with counts of loaded entries

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML is invalid
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Load YAML
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {e}")

        if not config:
            logger.warning(f"Empty configuration in {config_path}")
            return {"allowlist_entries": 0, "capability_mappings": 0}

        stats = {"allowlist_entries": 0, "capability_mappings": 0}

        # Clear existing if requested
        if clear_existing:
            await self._clear_all_entries()

        # Load agent allowlists
        agent_allowlists = config.get("agent_allowlists", {})
        stats["allowlist_entries"] = await self._load_allowlists(agent_allowlists)

        # Load capability mappings
        capability_mappings = config.get("capability_mappings", {})
        stats["capability_mappings"] = await self._load_capability_mappings(capability_mappings)

        logger.info(
            f"Loaded configuration from {config_path}: "
            f"{stats['allowlist_entries']} allowlist entries, "
            f"{stats['capability_mappings']} capability mappings"
        )

        return stats

    async def _load_allowlists(self, allowlists: Dict[str, List[Dict[str, Any]]]) -> int:
        """Load agent allowlist entries."""
        count = 0

        for agent_id, entries in allowlists.items():
            for entry in entries:
                skill_name = entry.get("skill")
                allowed = entry.get("allowed", True)
                notes = entry.get("notes")

                if not skill_name:
                    logger.warning(f"Skipping entry for {agent_id}: missing skill name")
                    continue

                try:
                    await self.allowlist_manager.add_allowlist_entry(
                        agent_id=agent_id,
                        skill_name=skill_name,
                        allowed=allowed,
                        created_by="config_loader",
                        notes=notes,
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to add allowlist entry for {agent_id}/{skill_name}: {e}")

        return count

    async def _load_capability_mappings(self, mappings: Dict[str, List[Dict[str, Any]]]) -> int:
        """Load capability-to-skill mappings."""
        count = 0

        for capability_name, skills in mappings.items():
            for skill_entry in skills:
                skill_name = skill_entry.get("skill")
                priority = skill_entry.get("priority", 10)
                metadata = skill_entry.get("metadata", {})

                if not skill_name:
                    logger.warning(f"Skipping entry for {capability_name}: missing skill name")
                    continue

                try:
                    await self.allowlist_manager.add_capability_mapping(
                        capability_name=capability_name,
                        skill_name=skill_name,
                        priority=priority,
                        metadata=metadata,
                    )
                    count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to add capability mapping " f"{capability_name}/{skill_name}: {e}"
                    )

        return count

    async def _clear_all_entries(self) -> None:
        """Clear all existing allowlist and capability mapping entries."""
        async with self.db_pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_skill_allowlist")
            await conn.execute("DELETE FROM capability_skill_mapping")

        self.allowlist_manager.clear_cache()
        logger.info("Cleared all existing allowlist and capability mapping entries")

    async def export_to_yaml(self, output_path: str) -> None:
        """
        Export current allowlist configuration to YAML file.

        Args:
            output_path: Path for output YAML file
        """
        config = {"agent_allowlists": {}, "capability_mappings": {}}

        # Export allowlists
        async with self.db_pool.acquire() as conn:
            # Get all allowlist entries
            allowlist_rows = await conn.fetch("""
                SELECT agent_id, skill_name, allowed, notes
                FROM agent_skill_allowlist
                ORDER BY agent_id, skill_name
                """)

            for row in allowlist_rows:
                agent_id = row["agent_id"]
                if agent_id not in config["agent_allowlists"]:
                    config["agent_allowlists"][agent_id] = []

                entry = {"skill": row["skill_name"], "allowed": row["allowed"]}
                if row["notes"]:
                    entry["notes"] = row["notes"]

                config["agent_allowlists"][agent_id].append(entry)

            # Get all capability mappings
            mapping_rows = await conn.fetch("""
                SELECT capability_name, skill_name, priority, metadata
                FROM capability_skill_mapping
                ORDER BY capability_name, priority, skill_name
                """)

            for row in mapping_rows:
                capability = row["capability_name"]
                if capability not in config["capability_mappings"]:
                    config["capability_mappings"][capability] = []

                entry = {"skill": row["skill_name"], "priority": row["priority"]}
                if row["metadata"]:
                    entry["metadata"] = row["metadata"]

                config["capability_mappings"][capability].append(entry)

        # Write YAML
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        logger.info(f"Exported configuration to {output_path}")
