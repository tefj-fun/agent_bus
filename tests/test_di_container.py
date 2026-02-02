"""Tests for the Dependency Injection Container."""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set test environment
os.environ.setdefault("LLM_MODE", "mock")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")


class TestContainerBasics:
    """Test basic container functionality."""

    @pytest.mark.asyncio
    async def test_container_initialization(self):
        """Test container can be created and initialized."""
        from src.infrastructure.container import Container

        test_container = Container()

        assert not test_container._initialized
        assert not test_container._closed

    @pytest.mark.asyncio
    async def test_container_register_and_resolve(self):
        """Test registering and resolving dependencies."""
        from src.infrastructure.container import Container, Lifecycle

        test_container = Container()

        # Register a simple dependency
        test_container.register(
            "test_dep",
            lambda: {"value": 42},
            Lifecycle.SINGLETON,
        )

        result = await test_container.resolve("test_dep")
        assert result == {"value": 42}

    @pytest.mark.asyncio
    async def test_singleton_lifecycle(self):
        """Test singleton dependencies return same instance."""
        from src.infrastructure.container import Container, Lifecycle

        test_container = Container()

        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"instance": call_count}

        test_container.register("singleton_test", factory, Lifecycle.SINGLETON)

        result1 = await test_container.resolve("singleton_test")
        result2 = await test_container.resolve("singleton_test")

        assert result1 is result2
        assert call_count == 1  # Factory called only once

    @pytest.mark.asyncio
    async def test_transient_lifecycle(self):
        """Test transient dependencies return new instances."""
        from src.infrastructure.container import Container, Lifecycle

        test_container = Container()

        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"instance": call_count}

        test_container.register("transient_test", factory, Lifecycle.TRANSIENT)

        result1 = await test_container.resolve("transient_test")
        result2 = await test_container.resolve("transient_test")

        assert result1 != result2
        assert call_count == 2  # Factory called twice

    @pytest.mark.asyncio
    async def test_override_dependency(self):
        """Test overriding a dependency."""
        from src.infrastructure.container import Container

        test_container = Container()

        mock_instance = MagicMock()
        test_container.override("redis", mock_instance)

        result = await test_container.redis()
        assert result is mock_instance

    @pytest.mark.asyncio
    async def test_async_factory(self):
        """Test async factory functions work correctly."""
        from src.infrastructure.container import Container, Lifecycle

        test_container = Container()

        async def async_factory():
            await asyncio.sleep(0.01)
            return {"async": True}

        test_container.register("async_dep", async_factory, Lifecycle.SINGLETON)

        result = await test_container.resolve("async_dep")
        assert result == {"async": True}

    @pytest.mark.asyncio
    async def test_resolve_unknown_dependency_raises(self):
        """Test resolving unknown dependency raises KeyError."""
        from src.infrastructure.container import Container

        test_container = Container()

        with pytest.raises(KeyError) as exc_info:
            await test_container.resolve("unknown_dep")

        assert "unknown_dep" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_container_reset(self):
        """Test container reset clears singleton instances."""
        from src.infrastructure.container import Container, Lifecycle

        test_container = Container()

        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return {"instance": call_count}

        test_container.register("reset_test", factory, Lifecycle.SINGLETON)

        # First resolve
        await test_container.resolve("reset_test")
        assert call_count == 1

        # Reset
        test_container.reset()

        # Second resolve should create new instance
        await test_container.resolve("reset_test")
        assert call_count == 2


class TestContainerWithMockedInfra:
    """Test container with mocked infrastructure."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when all services are healthy."""
        from src.infrastructure.container import Container

        test_container = Container()

        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        test_container.override("redis", mock_redis)

        # Mock PostgreSQL
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=None)
        test_container.override("postgres_pool", mock_pool)

        health = await test_container.health_check()

        assert health["redis"]["status"] == "healthy"
        assert health["postgres"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_redis_unhealthy(self):
        """Test health check when Redis is unhealthy."""
        from src.infrastructure.container import Container

        test_container = Container()

        # Mock Redis to fail
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Connection refused"))
        test_container.override("redis", mock_redis)

        # Mock PostgreSQL as healthy
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_conn.execute = AsyncMock(return_value=None)
        test_container.override("postgres_pool", mock_pool)

        health = await test_container.health_check()

        assert health["redis"]["status"] == "unhealthy"
        assert "error" in health["redis"]

    @pytest.mark.asyncio
    async def test_container_close(self):
        """Test container close cleans up resources."""
        from src.infrastructure.container import Container

        test_container = Container()

        # Mock dependencies with close methods
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        test_container.override("redis", mock_redis)

        mock_pool = AsyncMock()
        mock_pool.close = AsyncMock()
        test_container.override("postgres_pool", mock_pool)

        test_container._initialized = True

        await test_container.close()

        assert test_container._closed
        mock_redis.close.assert_called_once()
        mock_pool.close.assert_called_once()


class TestDependencyClass:
    """Test the Dependency wrapper class."""

    @pytest.mark.asyncio
    async def test_dependency_resolve_sync(self):
        """Test resolving sync factory."""
        from src.infrastructure.container import Dependency, Lifecycle

        dep = Dependency(factory=lambda: "value", lifecycle=Lifecycle.SINGLETON)

        result = await dep.resolve()
        assert result == "value"

    @pytest.mark.asyncio
    async def test_dependency_resolve_async(self):
        """Test resolving async factory."""
        from src.infrastructure.container import Dependency, Lifecycle

        async def async_factory():
            return "async_value"

        dep = Dependency(factory=async_factory, lifecycle=Lifecycle.SINGLETON)

        result = await dep.resolve()
        assert result == "async_value"

    @pytest.mark.asyncio
    async def test_dependency_thread_safety(self):
        """Test singleton dependency is thread-safe."""
        from src.infrastructure.container import Dependency, Lifecycle

        call_count = 0

        async def slow_factory():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return {"instance": call_count}

        dep = Dependency(factory=slow_factory, lifecycle=Lifecycle.SINGLETON)

        # Resolve concurrently
        results = await asyncio.gather(
            dep.resolve(),
            dep.resolve(),
            dep.resolve(),
        )

        # All should get same instance
        assert results[0] is results[1] is results[2]
        # Factory should only be called once
        assert call_count == 1


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_get_redis(self):
        """Test get_redis convenience function."""
        from src.infrastructure.container import container, get_redis

        mock_redis = AsyncMock()
        container.override("redis", mock_redis)

        result = await get_redis()
        assert result is mock_redis

        # Reset for other tests
        container.reset()

    @pytest.mark.asyncio
    async def test_get_postgres_pool(self):
        """Test get_postgres_pool convenience function."""
        from src.infrastructure.container import container, get_postgres_pool

        mock_pool = AsyncMock()
        container.override("postgres_pool", mock_pool)

        result = await get_postgres_pool()
        assert result is mock_pool

        # Reset for other tests
        container.reset()

    @pytest.mark.asyncio
    async def test_get_anthropic_mock_mode(self):
        """Test get_anthropic returns None in mock mode."""
        from src.infrastructure.container import container, get_anthropic
        from src.config import settings

        if settings.llm_mode == "mock":
            # In mock mode, should resolve to None
            container.override("anthropic", None)
            result = await get_anthropic()
            assert result is None

        container.reset()
