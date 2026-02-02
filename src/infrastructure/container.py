"""Dependency Injection Container for agent_bus.

This module provides a proper DI container that:
1. Lazily initializes connections (not at import time)
2. Provides explicit dependency resolution
3. Supports different lifecycles (singleton, request-scoped)
4. Enables easy testing with mock injection
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Optional, TypeVar
from enum import Enum

import redis.asyncio as redis
import asyncpg
from anthropic import AsyncAnthropic

from ..config import settings


T = TypeVar("T")


class Lifecycle(Enum):
    """Dependency lifecycle options."""

    SINGLETON = "singleton"  # One instance for the entire application
    TRANSIENT = "transient"  # New instance each time


@dataclass
class Dependency(Generic[T]):
    """Wrapper for a dependency with its lifecycle."""

    factory: Callable[..., T]
    lifecycle: Lifecycle = Lifecycle.SINGLETON
    _instance: Optional[T] = field(default=None, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def resolve(self) -> T:
        """Resolve the dependency, respecting lifecycle."""
        if self.lifecycle == Lifecycle.TRANSIENT:
            result = self.factory()
            if asyncio.iscoroutine(result):
                return await result
            return result

        # Singleton - use lock to prevent race conditions
        if self._instance is None:
            async with self._lock:
                if self._instance is None:
                    result = self.factory()
                    if asyncio.iscoroutine(result):
                        self._instance = await result
                    else:
                        self._instance = result
        return self._instance

    def reset(self) -> None:
        """Reset the singleton instance (useful for testing)."""
        self._instance = None


class Container:
    """
    Dependency Injection Container.

    Provides lazy initialization and explicit dependency resolution
    instead of module-level singletons.

    Usage:
        container = Container()
        await container.init()

        redis = await container.redis()
        postgres = await container.postgres_pool()

        # Cleanup
        await container.close()
    """

    def __init__(self) -> None:
        self._dependencies: Dict[str, Dependency] = {}
        self._initialized = False
        self._closed = False

        # Register default dependencies
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default infrastructure dependencies."""

        # Redis client
        self.register(
            "redis",
            lambda: redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            ),
            Lifecycle.SINGLETON,
        )

        # PostgreSQL pool (async factory)
        async def create_pool() -> asyncpg.Pool:
            return await asyncpg.create_pool(
                settings.postgres_url,
                min_size=settings.postgres_pool_min_size,
                max_size=settings.postgres_pool_max_size,
                command_timeout=settings.postgres_command_timeout,
            )

        self.register("postgres_pool", create_pool, Lifecycle.SINGLETON)

        # Anthropic client
        def create_anthropic() -> Optional[AsyncAnthropic]:
            if settings.llm_mode == "mock":
                return None
            return AsyncAnthropic(api_key=settings.anthropic_api_key)

        self.register("anthropic", create_anthropic, Lifecycle.SINGLETON)

    def register(
        self,
        name: str,
        factory: Callable[..., T],
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> None:
        """
        Register a dependency.

        Args:
            name: Unique name for the dependency
            factory: Factory function to create the dependency
            lifecycle: How the dependency should be managed
        """
        self._dependencies[name] = Dependency(factory=factory, lifecycle=lifecycle)

    def override(self, name: str, instance: Any) -> None:
        """
        Override a dependency with a specific instance (for testing).

        Args:
            name: Dependency name to override
            instance: Instance to use
        """
        if name in self._dependencies:
            self._dependencies[name]._instance = instance
        else:
            # Create a new singleton dependency with the instance
            dep = Dependency(factory=lambda: instance, lifecycle=Lifecycle.SINGLETON)
            dep._instance = instance
            self._dependencies[name] = dep

    async def resolve(self, name: str) -> Any:
        """
        Resolve a dependency by name.

        Args:
            name: Dependency name

        Returns:
            The resolved dependency instance

        Raises:
            KeyError: If dependency is not registered
        """
        if name not in self._dependencies:
            raise KeyError(f"Dependency '{name}' not registered")
        return await self._dependencies[name].resolve()

    async def redis(self) -> redis.Redis:
        """Get Redis client."""
        return await self.resolve("redis")

    async def postgres_pool(self) -> asyncpg.Pool:
        """Get PostgreSQL connection pool."""
        return await self.resolve("postgres_pool")

    async def anthropic(self) -> Optional[AsyncAnthropic]:
        """Get Anthropic client (None in mock mode)."""
        return await self.resolve("anthropic")

    async def init(self) -> None:
        """
        Initialize all singleton dependencies.

        Call this during application startup to eagerly initialize
        connections and fail fast if infrastructure is unavailable.
        """
        if self._initialized:
            return

        # Initialize core infrastructure
        await self.redis()
        await self.postgres_pool()
        await self.anthropic()

        self._initialized = True

    async def close(self) -> None:
        """
        Close all connections and cleanup resources.

        Call this during application shutdown.
        """
        if self._closed:
            return

        # Close Redis
        try:
            redis_client = self._dependencies.get("redis")
            if redis_client and redis_client._instance:
                await redis_client._instance.close()
        except Exception:
            pass  # Best effort cleanup

        # Close PostgreSQL pool
        try:
            pg_pool = self._dependencies.get("postgres_pool")
            if pg_pool and pg_pool._instance:
                await pg_pool._instance.close()
        except Exception:
            pass  # Best effort cleanup

        # Reset all dependencies
        for dep in self._dependencies.values():
            dep.reset()

        self._closed = True
        self._initialized = False

    def reset(self) -> None:
        """Reset the container (for testing)."""
        for dep in self._dependencies.values():
            dep.reset()
        self._initialized = False
        self._closed = False

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health checks on all infrastructure.

        Returns:
            Dict with health status for each service
        """
        result = {
            "redis": {"status": "unknown"},
            "postgres": {"status": "unknown"},
        }

        # Check Redis
        try:
            client = await self.redis()
            pong = await client.ping()
            result["redis"] = {
                "status": "healthy" if pong else "unhealthy",
            }
        except Exception as e:
            result["redis"] = {"status": "unhealthy", "error": str(e)}

        # Check PostgreSQL
        try:
            pool = await self.postgres_pool()
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
            result["postgres"] = {"status": "healthy"}
        except Exception as e:
            result["postgres"] = {"status": "unhealthy", "error": str(e)}

        return result


# Global container instance
# Note: This is still a module-level singleton, but it's a container
# that lazily initializes dependencies rather than eagerly connecting
container = Container()


# Convenience functions for backwards compatibility
async def get_redis() -> redis.Redis:
    """Get Redis client from container."""
    return await container.redis()


async def get_postgres_pool() -> asyncpg.Pool:
    """Get PostgreSQL pool from container."""
    return await container.postgres_pool()


async def get_anthropic() -> Optional[AsyncAnthropic]:
    """Get Anthropic client from container."""
    return await container.anthropic()
