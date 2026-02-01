"""Agent skill allowlist and capability mapping management."""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class AllowlistEntry:
    """Entry in the agent skill allowlist."""
    
    id: int
    agent_id: str
    skill_name: str
    allowed: bool
    created_by: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class CapabilityMapping:
    """Mapping between capability and skill."""
    
    id: int
    capability_name: str
    skill_name: str
    priority: int
    metadata: Dict[str, Any]


class SkillPermissionError(Exception):
    """Agent does not have permission to use requested skill."""
    pass


class SkillAllowlistManager:
    """
    Manages per-agent skill allowlists and capability-based skill discovery.
    
    Features:
    - Per-agent skill permission enforcement
    - Capability-based skill discovery
    - Wildcard allowlist support (* = all skills)
    - Database-backed configuration
    - Backward compatibility (agents without allowlist have full access)
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self._cache_enabled = True
        self._allowlist_cache: Dict[str, Dict[str, bool]] = {}
        self._capability_cache: Dict[str, List[str]] = {}
    
    async def check_permission(
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
            True if permitted, False otherwise
            
        Algorithm:
        1. Check cache first
        2. Query database for explicit allowlist entry
        3. Check for wildcard entry (agent_id + *)
        4. Default to True (backward compatibility - allow if no entry)
        """
        # Check cache
        cache_key = f"{agent_id}:{skill_name}"
        if self._cache_enabled and cache_key in self._allowlist_cache.get(agent_id, {}):
            return self._allowlist_cache[agent_id][cache_key]
        
        async with self.db_pool.acquire() as conn:
            # Check for exact match
            row = await conn.fetchrow(
                """
                SELECT allowed FROM agent_skill_allowlist
                WHERE agent_id = $1 AND skill_name = $2
                """,
                agent_id,
                skill_name
            )
            
            if row is not None:
                allowed = row['allowed']
                self._cache_result(agent_id, cache_key, allowed)
                return allowed
            
            # Check for wildcard entry (agent can use all skills)
            wildcard_row = await conn.fetchrow(
                """
                SELECT allowed FROM agent_skill_allowlist
                WHERE agent_id = $1 AND skill_name = '*'
                """,
                agent_id
            )
            
            if wildcard_row is not None:
                allowed = wildcard_row['allowed']
                self._cache_result(agent_id, cache_key, allowed)
                return allowed
            
            # Default: allow (backward compatibility)
            # Agents without explicit allowlist entries can use any skill
            self._cache_result(agent_id, cache_key, True)
            return True
    
    async def enforce_permission(
        self,
        agent_id: str,
        skill_name: str
    ) -> None:
        """
        Enforce skill permission, raising exception if denied.
        
        Args:
            agent_id: Agent identifier
            skill_name: Skill name
            
        Raises:
            SkillPermissionError: If agent lacks permission
        """
        if not await self.check_permission(agent_id, skill_name):
            logger.warning(
                f"Permission denied: agent '{agent_id}' cannot use skill '{skill_name}'"
            )
            raise SkillPermissionError(
                f"Agent '{agent_id}' is not allowed to use skill '{skill_name}'"
            )
    
    async def add_allowlist_entry(
        self,
        agent_id: str,
        skill_name: str,
        allowed: bool = True,
        created_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Add or update an allowlist entry.
        
        Args:
            agent_id: Agent identifier
            skill_name: Skill name (or '*' for wildcard)
            allowed: Whether to allow or deny
            created_by: Who created this entry
            notes: Optional notes
            
        Returns:
            Entry ID
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO agent_skill_allowlist 
                    (agent_id, skill_name, allowed, created_by, notes)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (agent_id, skill_name) 
                DO UPDATE SET 
                    allowed = $3,
                    created_by = $4,
                    notes = $5
                RETURNING id
                """,
                agent_id,
                skill_name,
                allowed,
                created_by,
                notes
            )
            
            # Invalidate cache
            self._invalidate_agent_cache(agent_id)
            
            logger.info(
                f"Allowlist entry {'added' if allowed else 'denied'}: "
                f"agent='{agent_id}', skill='{skill_name}'"
            )
            
            return row['id']
    
    async def remove_allowlist_entry(
        self,
        agent_id: str,
        skill_name: str
    ) -> bool:
        """
        Remove an allowlist entry.
        
        Args:
            agent_id: Agent identifier
            skill_name: Skill name
            
        Returns:
            True if entry was removed, False if not found
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM agent_skill_allowlist
                WHERE agent_id = $1 AND skill_name = $2
                """,
                agent_id,
                skill_name
            )
            
            # Invalidate cache
            self._invalidate_agent_cache(agent_id)
            
            removed = result.split()[-1] != '0'
            if removed:
                logger.info(
                    f"Allowlist entry removed: agent='{agent_id}', skill='{skill_name}'"
                )
            
            return removed
    
    async def get_agent_allowed_skills(
        self,
        agent_id: str
    ) -> List[str]:
        """
        Get list of skills explicitly allowed for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            List of allowed skill names (empty if using default allow-all)
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT skill_name FROM agent_skill_allowlist
                WHERE agent_id = $1 AND allowed = TRUE
                ORDER BY skill_name
                """,
                agent_id
            )
            
            return [row['skill_name'] for row in rows]
    
    async def get_skills_by_capability(
        self,
        capability: str,
        agent_id: Optional[str] = None
    ) -> List[str]:
        """
        Find skills that provide a capability, optionally filtered by agent permissions.
        
        Args:
            capability: Capability name (e.g., 'ui-design')
            agent_id: Optional agent ID to filter by permissions
            
        Returns:
            List of skill names, ordered by priority (lower = higher)
        """
        # Check cache
        if self._cache_enabled and capability in self._capability_cache:
            skills = self._capability_cache[capability]
        else:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT skill_name, priority
                    FROM capability_skill_mapping
                    WHERE capability_name = $1
                    ORDER BY priority ASC, skill_name ASC
                    """,
                    capability
                )
                
                skills = [row['skill_name'] for row in rows]
                
                # Cache the result
                if self._cache_enabled:
                    self._capability_cache[capability] = skills
        
        # Filter by agent permissions if provided
        if agent_id:
            permitted_skills = []
            for skill in skills:
                if await self.check_permission(agent_id, skill):
                    permitted_skills.append(skill)
            return permitted_skills
        
        return skills
    
    async def add_capability_mapping(
        self,
        capability_name: str,
        skill_name: str,
        priority: int = 10,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add a capability-to-skill mapping.
        
        Args:
            capability_name: Capability identifier
            skill_name: Skill name
            priority: Priority (lower = higher priority)
            metadata: Optional metadata
            
        Returns:
            Mapping ID
        """
        import json
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO capability_skill_mapping
                    (capability_name, skill_name, priority, metadata)
                VALUES ($1, $2, $3, $4::jsonb)
                ON CONFLICT (capability_name, skill_name)
                DO UPDATE SET
                    priority = $3,
                    metadata = $4::jsonb
                RETURNING id
                """,
                capability_name,
                skill_name,
                priority,
                json.dumps(metadata or {})
            )
            
            # Invalidate cache
            if capability_name in self._capability_cache:
                del self._capability_cache[capability_name]
            
            logger.info(
                f"Capability mapping added: '{capability_name}' -> '{skill_name}' "
                f"(priority={priority})"
            )
            
            return row['id']
    
    async def remove_capability_mapping(
        self,
        capability_name: str,
        skill_name: str
    ) -> bool:
        """
        Remove a capability-to-skill mapping.
        
        Args:
            capability_name: Capability identifier
            skill_name: Skill name
            
        Returns:
            True if removed, False if not found
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM capability_skill_mapping
                WHERE capability_name = $1 AND skill_name = $2
                """,
                capability_name,
                skill_name
            )
            
            # Invalidate cache
            if capability_name in self._capability_cache:
                del self._capability_cache[capability_name]
            
            removed = result.split()[-1] != '0'
            if removed:
                logger.info(
                    f"Capability mapping removed: '{capability_name}' -> '{skill_name}'"
                )
            
            return removed
    
    async def get_all_capabilities(self) -> List[str]:
        """
        Get list of all registered capabilities.
        
        Returns:
            List of unique capability names
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT capability_name
                FROM capability_skill_mapping
                ORDER BY capability_name
                """
            )
            
            return [row['capability_name'] for row in rows]
    
    def clear_cache(self) -> None:
        """Clear all internal caches."""
        self._allowlist_cache.clear()
        self._capability_cache.clear()
        logger.debug("Allowlist caches cleared")
    
    def _cache_result(self, agent_id: str, cache_key: str, allowed: bool) -> None:
        """Cache a permission check result."""
        if not self._cache_enabled:
            return
        
        if agent_id not in self._allowlist_cache:
            self._allowlist_cache[agent_id] = {}
        
        self._allowlist_cache[agent_id][cache_key] = allowed
    
    def _invalidate_agent_cache(self, agent_id: str) -> None:
        """Invalidate cache for a specific agent."""
        if agent_id in self._allowlist_cache:
            del self._allowlist_cache[agent_id]
