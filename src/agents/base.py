"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from anthropic import AsyncAnthropic
import json
import asyncio
import redis.asyncio as redis
import asyncpg

from ..skills.manager import SkillsManager
from ..config import settings


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
        max_tokens: int = 8192,
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
        timeout_s = 180
        try:
            response = await asyncio.wait_for(_call_with_thinking(), timeout=timeout_s)
        except TypeError:
            try:
                response = await asyncio.wait_for(_call_no_thinking(), timeout=timeout_s)
            except asyncio.TimeoutError as e:
                raise TimeoutError(f"LLM call timed out after {timeout_s}s") from e
        except asyncio.TimeoutError as e:
            raise TimeoutError(f"LLM call timed out after {timeout_s}s") from e

        return self._extract_response(response)

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

    async def load_skill(self, skill_name: str) -> Optional[Any]:
        """
        Load a Claude Skill.

        Args:
            skill_name: Name of the skill to load

        Returns:
            Loaded skill or None
        """
        return await self.context.skills_manager.load_skill(skill_name)

    async def execute_with_skill(
        self,
        skill_name: str,
        prompt: str,
        context_data: Dict[str, Any]
    ) -> str:
        """
        Execute a task using a specific skill.

        Args:
            skill_name: Name of the skill to use
            prompt: Main task prompt
            context_data: Additional context for the skill

        Returns:
            Response from Claude using the skill
        """
        skill = await self.load_skill(skill_name)
        if not skill:
            raise ValueError(f"Skill '{skill_name}' not found")

        # Combine skill prompt with task prompt
        skill_prompt = skill.get_prompt()
        combined_prompt = f"{skill_prompt}\n\n---\n\n{prompt}"

        # Use the skill's system prompt if available
        system_prompt = f"You are an AI agent specialized in {skill_name}."

        return await self.query_llm(
            prompt=combined_prompt,
            system=system_prompt,
            thinking_budget=2048
        )

    async def save_artifact(
        self,
        artifact_type: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Save agent output as artifact.

        Args:
            artifact_type: Type of artifact (prd, code, test, etc.)
            content: Artifact content
            metadata: Additional metadata

        Returns:
            Artifact ID
        """
        artifact_id = f"{self.agent_id}_{artifact_type}_{self.context.job_id}"

        # Save to PostgreSQL
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
                json.dumps(metadata or {})
            )

        return artifact_id

    async def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an artifact by ID.

        Args:
            artifact_id: ID of the artifact

        Returns:
            Artifact data or None
        """
        async with self.context.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, agent_id, job_id, type, content, metadata, created_at
                FROM artifacts
                WHERE id = $1
                """,
                artifact_id
            )

            if row:
                return dict(row)
            return None

    async def notify_completion(self, result: AgentResult) -> None:
        """
        Notify master agent of task completion.

        Args:
            result: Result of the task execution
        """
        import json
        payload = json.dumps(result.__dict__)

        await self.context.redis_client.publish(
            "agent_bus:events:task_completed",
            payload
        )

        # Note: the worker process is responsible for writing the authoritative
        # agent_bus:results:{task_id} payload (typically result.output) for the master agent.

    async def log_event(
        self,
        event_type: str,
        message: str,
        data: Optional[Dict] = None
    ) -> None:
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
            "timestamp": "NOW()"
        }

        import json

        # Write to Postgres agent_events for durability/search
        import json
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
                json.dumps(data or {})
            )

        # Also keep a lightweight Redis log stream
        await self.context.redis_client.lpush(
            f"agent_bus:logs:{self.context.job_id}",
            json.dumps(event)
        )

        print(f"[{self.agent_id}] {event_type.upper()}: {message}")
