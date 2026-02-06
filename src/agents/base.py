"""Base agent class for all specialized agents."""
from __future__ import annotations


from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
# from functools import lru_cache
from anthropic import AsyncAnthropic
import json
import asyncio
import redis.asyncio as redis
import asyncpg

from ..skills.manager import SkillsManager
from ..config import settings
from ..storage.artifact_store import get_artifact_store, ArtifactStore


@dataclass
class AgentContext:
    """Shared context across all agents."""

    project_id: str
    job_id: str
    session_key: str
    workspace_dir: str
    redis_client: redis.Redis
    db_pool: asyncpg.Pool
    anthropic_client: AsyncAnthropic
    skills_manager: SkillsManager
    config: Dict[str, Any]


@dataclass
class AgentTask:
    """Task definition for agents."""

    task_id: str
    task_type: str
    input_data: Dict[str, Any]
    dependencies: List[str]  # Task IDs this depends on
    priority: int
    metadata: Dict[str, Any]


@dataclass
class AgentResult:
    """Result from agent execution."""

    task_id: str
    agent_id: str
    success: bool
    output: Dict[str, Any]
    artifacts: List[str]  # IDs of created artifacts
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class BaseAgent(ABC):
    """Base class for all specialized agents."""

    def __init__(self, context: AgentContext):
        self.context = context
        self.agent_id = self.get_agent_id()
        self.capabilities = self.define_capabilities()
        self._active_task_id: Optional[str] = None

    def _set_active_task_id(self, task_id: str) -> None:
        """Track the active task id for usage attribution."""
        self._active_task_id = task_id

    @abstractmethod
    def get_agent_id(self) -> str:
        """Return unique agent identifier."""
        pass

    @abstractmethod
    def define_capabilities(self) -> Dict[str, Any]:
        """Define what this agent can do."""
        pass

    @abstractmethod
    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute the agent's primary function."""
        pass

    async def query_llm(
        self,
        prompt: str,
        system: str,
        model: Optional[str] = None,
        thinking_budget: int = 1024,
        max_tokens: Optional[int] = None,
        task_id: Optional[str] = None,
    ) -> str:
        """
        Query Claude with extended thinking support.

        Args:
            prompt: User prompt
            system: System prompt
            model: Model to use (defaults to config)
            thinking_budget: Tokens allocated for thinking
            max_tokens: Maximum output tokens

        Returns:
            Response text from Claude
        """
        # Provider routing
        provider = settings.llm_provider
        if max_tokens is None:
            max_tokens = settings.anthropic_max_tokens

        resolved_task_id = task_id or self._active_task_id

        if provider == "openai":
            from ..infrastructure.openai_client import openai_chat_complete

            # model parameter maps to OPENAI_MODEL for openai provider
            result = await openai_chat_complete(
                prompt=prompt,
                system=system,
                model=model,
                max_tokens=max_tokens,
                return_usage=True,
            )
            if isinstance(result, tuple):
                text, usage = result
                normalized = self._normalize_usage(
                    usage=usage, provider="openai", model=model or settings.openai_model
                )
                await self._record_llm_usage(resolved_task_id, normalized)
                return text
            return result

        # default: anthropic
        if model is None:
            model = settings.anthropic_model

        # anthropic SDK may or may not support the `thinking` parameter depending on version/model.
        # Try with thinking first, then fall back.
        async def _call_with_thinking():
            return await self.context.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                thinking={
                    "type": "enabled",
                    "budget_tokens": thinking_budget,
                },
            )

        async def _call_no_thinking():
            return await self.context.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )

        # Guard against indefinite hangs (network/provider stalls)
        timeout_s = settings.timeout_llm_call
        try:
            response = await asyncio.wait_for(_call_with_thinking(), timeout=timeout_s)
        except TypeError:
            try:
                response = await asyncio.wait_for(_call_no_thinking(), timeout=timeout_s)
            except asyncio.TimeoutError as e:
                raise TimeoutError(f"LLM call timed out after {timeout_s}s") from e
        except asyncio.TimeoutError as e:
            raise TimeoutError(f"LLM call timed out after {timeout_s}s") from e

        text = self._extract_response(response)
        usage = self._extract_usage(response)
        normalized = self._normalize_usage(usage=usage, provider="anthropic", model=model)
        await self._record_llm_usage(resolved_task_id, normalized)
        return text

    def _extract_usage(self, response: Any) -> Optional[Dict[str, Any]]:
        """Extract usage information from LLM response."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return None

        def _get(key: str) -> Optional[int]:
            if isinstance(usage, dict):
                return usage.get(key)
            return getattr(usage, key, None)

        input_tokens = _get("input_tokens")
        output_tokens = _get("output_tokens")
        cache_creation_input_tokens = _get("cache_creation_input_tokens")
        cache_read_input_tokens = _get("cache_read_input_tokens")

        payload: Dict[str, Any] = {}
        if input_tokens is not None:
            payload["input_tokens"] = input_tokens
        if output_tokens is not None:
            payload["output_tokens"] = output_tokens
        if cache_creation_input_tokens is not None:
            payload["cache_creation_input_tokens"] = cache_creation_input_tokens
        if cache_read_input_tokens is not None:
            payload["cache_read_input_tokens"] = cache_read_input_tokens

        return payload or None

    def _normalize_usage(
        self,
        usage: Optional[Dict[str, Any]],
        provider: str,
        model: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Normalize usage payload into consistent schema."""
        if not usage:
            return None

        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))

        normalized: Dict[str, Any] = {
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

        # Preserve extra usage fields if present
        for key in ("cache_creation_input_tokens", "cache_read_input_tokens"):
            if key in usage and usage[key] is not None:
                normalized[key] = int(usage[key])

        cost_usd = self._calculate_cost_usd(provider, model, input_tokens, output_tokens)
        if cost_usd is not None:
            normalized["cost_usd"] = cost_usd

        return normalized

    @staticmethod
    def _pricing_config() -> Dict[str, Any]:
        from ..infrastructure.pricing import get_pricing

        return get_pricing()

    def _calculate_cost_usd(
        self,
        provider: str,
        model: Optional[str],
        input_tokens: int,
        output_tokens: int,
    ) -> Optional[float]:
        """Calculate approximate cost in USD if pricing is configured."""
        if not model:
            return None
        pricing = self._pricing_config()
        provider_pricing = pricing.get(provider, {})
        model_pricing = provider_pricing.get(model) or provider_pricing.get("*")
        if not isinstance(model_pricing, dict):
            return None
        input_rate = model_pricing.get("input_per_1k")
        output_rate = model_pricing.get("output_per_1k")
        if input_rate is None or output_rate is None:
            return None
        try:
            return (input_tokens / 1000.0) * float(input_rate) + (output_tokens / 1000.0) * float(output_rate)
        except Exception:
            return None

    async def _record_llm_usage(
        self, task_id: Optional[str], usage: Optional[Dict[str, Any]]
    ) -> None:
        """Persist LLM usage to task metadata (best-effort)."""
        if not task_id or not usage:
            return

        try:
            async with self.context.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT metadata FROM tasks WHERE id = $1",
                    task_id,
                )
                if not row:
                    return
                metadata = row.get("metadata") or {}
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)

                llm_usage = metadata.get("llm_usage") or {}

                def _to_int(value: Any) -> int:
                    try:
                        return int(value)
                    except Exception:
                        return 0

                def _to_float(value: Any) -> float:
                    try:
                        return float(value)
                    except Exception:
                        return 0.0

                llm_usage["input_tokens"] = _to_int(llm_usage.get("input_tokens")) + _to_int(
                    usage.get("input_tokens")
                )
                llm_usage["output_tokens"] = _to_int(llm_usage.get("output_tokens")) + _to_int(
                    usage.get("output_tokens")
                )
                llm_usage["total_tokens"] = _to_int(llm_usage.get("total_tokens")) + _to_int(
                    usage.get("total_tokens")
                )
                llm_usage["calls"] = _to_int(llm_usage.get("calls")) + 1
                llm_usage["last_provider"] = usage.get("provider")
                llm_usage["last_model"] = usage.get("model")

                if usage.get("cost_usd") is not None:
                    llm_usage["cost_usd"] = _to_float(llm_usage.get("cost_usd")) + _to_float(
                        usage.get("cost_usd")
                    )

                metadata["llm_usage"] = llm_usage

                await conn.execute(
                    """
                    UPDATE tasks
                    SET metadata = $2::jsonb
                    WHERE id = $1
                    """,
                    task_id,
                    json.dumps(metadata),
                )
        except Exception:
            # Best-effort: usage tracking should not break task execution
            pass

    def _extract_response(self, response: Any) -> str:
        """Extract text response from Claude API response."""
        # Extract text from response content blocks
        text_parts = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif hasattr(block, "text"):
                text_parts.append(block.text)

        return "\n".join(text_parts)

    def _truth_system_guardrails(self) -> str:
        """Guardrails to ensure PRD and user requirements are the source of truth."""
        return (
            "Source of truth:\n"
            "- The user requirements and the PRD are authoritative.\n"
            "- Treat all other inputs as secondary/derived. If conflicts arise, call them out "
            "and align to requirements/PRD.\n"
            "- Do not invent requirements or scope beyond what is explicitly stated.\n"
        )

    async def load_skill(self, skill_name: str, enforce_permissions: bool = True) -> Optional[Any]:
        """
        Load a Claude Skill with permission enforcement.

        Args:
            skill_name: Name of the skill to load
            enforce_permissions: Whether to enforce allowlist permissions

        Returns:
            Loaded skill or None

        Raises:
            SkillPermissionError: If agent lacks permission to use skill
        """
        return await self.context.skills_manager.load_skill(
            skill_name, agent_id=self.agent_id, enforce_permissions=enforce_permissions
        )

    async def execute_with_skill(
        self,
        skill_name: str,
        prompt: str,
        context_data: Dict[str, Any],
        enforce_permissions: bool = True,
    ) -> str:
        """
        Execute a task using a specific skill.

        Args:
            skill_name: Name of the skill to use
            prompt: Main task prompt
            context_data: Additional context for the skill
            enforce_permissions: Whether to enforce allowlist permissions

        Returns:
            Response from Claude using the skill

        Raises:
            SkillPermissionError: If agent lacks permission to use skill
        """
        skill = await self.load_skill(skill_name, enforce_permissions=enforce_permissions)
        if not skill:
            raise ValueError(f"Skill '{skill_name}' not found")

        # Combine skill prompt with task prompt
        skill_prompt = skill.get_prompt()
        combined_prompt = f"{skill_prompt}\n\n---\n\n{prompt}"

        # Use the skill's system prompt if available
        system_prompt = f"You are an AI agent specialized in {skill_name}."

        return await self.query_llm(
            prompt=combined_prompt, system=system_prompt, thinking_budget=2048
        )

    async def find_skills_by_capability(self, capability: str) -> list[str]:
        """
        Find skills that provide a specific capability.

        This respects the agent's skill allowlist.

        Args:
            capability: Capability name (e.g., 'ui-design', 'testing')

        Returns:
            List of skill names that this agent can use
        """
        return await self.context.skills_manager.find_skills_for_capability(
            capability, agent_id=self.agent_id
        )

    async def get_allowed_skills(self) -> list[str]:
        """
        Get list of skills this agent is allowed to use.

        Returns:
            List of allowed skill names (empty if no restrictions)
        """
        return await self.context.skills_manager.get_allowed_skills(self.agent_id)

    async def save_artifact(
        self,
        artifact_type: str,
        content: str,
        metadata: Optional[Dict] = None,
        artifact_id: Optional[str] = None,
    ) -> str:
        """
        Save agent output as artifact.

        Uses file-based storage for portability, with optional PostgreSQL
        metadata for querying. Configure via ARTIFACT_STORAGE_BACKEND env var.

        Args:
            artifact_type: Type of artifact (prd, code, test, etc.)
            content: Artifact content
            metadata: Additional metadata

        Returns:
            Artifact ID
        """
        if not artifact_id:
            artifact_id = f"{self.agent_id}_{artifact_type}_{self.context.job_id}"

        metadata = metadata or {}
        truth_hash = self.context.config.get("truth_prd_hash") if self.context.config else None
        truth_requirements_hash = (
            self.context.config.get("truth_requirements_hash") if self.context.config else None
        )
        truth_prd_artifact_id = (
            self.context.config.get("truth_prd_artifact_id") if self.context.config else None
        )
        if truth_hash and "truth_prd_hash" not in metadata:
            metadata["truth_prd_hash"] = truth_hash
        if truth_requirements_hash and "truth_requirements_hash" not in metadata:
            metadata["truth_requirements_hash"] = truth_requirements_hash
        if truth_prd_artifact_id and "truth_prd_artifact_id" not in metadata:
            metadata["truth_prd_artifact_id"] = truth_prd_artifact_id

        # Use file-based artifact store if configured
        if settings.artifact_storage_backend == "file":
            try:
                store = get_artifact_store()
                artifact_meta = await store.save(
                    artifact_id=artifact_id,
                    agent_id=self.agent_id,
                    job_id=self.context.job_id,
                    artifact_type=artifact_type,
                    content=content,
                    metadata=metadata,
                )

                # Also save metadata reference to PostgreSQL for querying
                async with self.context.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO artifacts (id, agent_id, job_id, type, content, metadata, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6::jsonb, NOW())
                        ON CONFLICT (id) DO UPDATE
                        SET content = $5, metadata = $6::jsonb, updated_at = NOW()
                        """,
                        artifact_id,
                        self.agent_id,
                        self.context.job_id,
                        artifact_type,
                        f"[file:{artifact_meta.file_path}]",  # Reference to file
                        json.dumps({
                            **(metadata or {}),
                            "_storage": "file",
                            "_file_path": artifact_meta.file_path,
                        }),
                    )
                return artifact_id
            except RuntimeError:
                # Artifact store not initialized, fall back to PostgreSQL
                pass

        # Fall back to PostgreSQL storage
        async with self.context.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO artifacts (id, agent_id, job_id, type, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, NOW())
                ON CONFLICT (id) DO UPDATE
                SET content = $5, metadata = $6::jsonb, updated_at = NOW()
                """,
                artifact_id,
                self.agent_id,
                self.context.job_id,
                artifact_type,
                content,
                json.dumps(metadata or {}),
            )

        return artifact_id

    async def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an artifact by ID.

        Checks file storage first (if configured), then falls back to PostgreSQL.

        Args:
            artifact_id: ID of the artifact

        Returns:
            Artifact data or None
        """
        # Try file storage first if configured
        if settings.artifact_storage_backend == "file":
            try:
                store = get_artifact_store()
                artifact = await store.get(artifact_id)
                if artifact:
                    return artifact
            except RuntimeError:
                pass

        # Fall back to PostgreSQL
        async with self.context.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, agent_id, job_id, type, content, metadata, created_at
                FROM artifacts
                WHERE id = $1
                """,
                artifact_id,
            )

            if row:
                result = dict(row)
                # Check if content is a file reference
                if result.get("content", "").startswith("[file:"):
                    # Try to load from file storage
                    try:
                        store = get_artifact_store()
                        artifact = await store.get(artifact_id)
                        if artifact:
                            return artifact
                    except RuntimeError:
                        pass
                return result
            return None

    async def notify_completion(self, result: AgentResult) -> None:
        """
        Notify master agent of task completion.

        Args:
            result: Result of the task execution
        """
        import json

        payload = json.dumps(result.__dict__)

        await self.context.redis_client.publish("agent_bus:events:task_completed", payload)

        # Note: the worker process is responsible for writing the authoritative
        # agent_bus:results:{task_id} payload (typically result.output) for the master agent.

    async def log_event(self, event_type: str, message: str, data: Optional[Dict] = None) -> None:
        """
        Log an agent event.

        Args:
            event_type: Type of event (info, warning, error)
            message: Event message
            data: Additional event data
        """
        event = {
            "agent_id": self.agent_id,
            "job_id": self.context.job_id,
            "event_type": event_type,
            "message": message,
            "data": data or {},
            "timestamp": "NOW()",
        }

        import json

        # Write to Postgres agent_events for durability/search

        async with self.context.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agent_events (agent_id, job_id, event_type, message, data)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                """,
                self.agent_id,
                self.context.job_id,
                event_type,
                message,
                json.dumps(data or {}),
            )

        # Also publish to the SSE event stream for live UI updates
        try:
            from datetime import datetime, timezone

            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "type": "agent_event",
                "data": {
                    "job_id": self.context.job_id,
                    "agent": self.agent_id,
                    "message": message,
                    "level": event_type,
                    "extra": data or {},
                },
            }
            await self.context.redis_client.publish_event("agent_bus:events", payload)
        except Exception:
            # Avoid breaking core flow if event publication fails
            pass

        # Also keep a lightweight Redis log stream
        await self.context.redis_client.lpush(
            f"agent_bus:logs:{self.context.job_id}", json.dumps(event)
        )

        print(f"[{self.agent_id}] {event_type.upper()}: {message}")
