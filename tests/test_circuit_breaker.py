"""Tests for Circuit Breaker implementation."""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock

# Set test environment
os.environ.setdefault("LLM_MODE", "mock")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")

from src.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitState,
    CircuitStats,
    circuit_registry,
)


class TestCircuitBreakerStates:
    """Test circuit breaker state transitions."""

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_stays_closed_on_success(self):
        """Test circuit stays closed on successful calls."""
        cb = CircuitBreaker("test", failure_threshold=3)

        async def success():
            return "ok"

        for _ in range(10):
            await cb.call(success)

        assert cb.state == CircuitState.CLOSED
        assert cb.stats.successes == 10
        assert cb.stats.failures == 0

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        """Test circuit opens after failure threshold reached."""
        cb = CircuitBreaker("test", failure_threshold=3)

        async def fail():
            raise Exception("error")

        for i in range(3):
            try:
                await cb.call(fail)
            except Exception:
                pass

        assert cb.state == CircuitState.OPEN
        assert cb.stats.failures >= 3

    @pytest.mark.asyncio
    async def test_open_circuit_raises_error(self):
        """Test open circuit raises CircuitBreakerError."""
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=10)

        async def fail():
            raise Exception("error")

        # Open the circuit
        try:
            await cb.call(fail)
        except Exception:
            pass

        assert cb.state == CircuitState.OPEN

        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError) as exc_info:
            await cb.call(lambda: "success")

        assert exc_info.value.circuit_name == "test"
        assert exc_info.value.recovery_time > 0

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker(
            "test",
            failure_threshold=1,
            recovery_timeout=0.1,  # 100ms
        )

        async def fail():
            raise Exception("error")

        # Open the circuit
        try:
            await cb.call(fail)
        except Exception:
            pass

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Check state (triggers transition check)
        await cb._check_state()

        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_closes_on_success(self):
        """Test circuit closes from HALF_OPEN on successful call."""
        cb = CircuitBreaker(
            "test",
            failure_threshold=1,
            recovery_timeout=0.05,
            half_open_requests=1,
        )

        # Open the circuit
        async def fail():
            raise Exception("error")

        try:
            await cb.call(fail)
        except Exception:
            pass

        # Wait and transition to half-open
        await asyncio.sleep(0.1)

        # Successful call should close circuit
        async def success():
            return "ok"

        result = await cb.call(success)

        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_reopens_on_failure(self):
        """Test circuit reopens from HALF_OPEN on failure."""
        cb = CircuitBreaker(
            "test",
            failure_threshold=1,
            recovery_timeout=0.05,
            half_open_requests=1,
        )

        async def fail():
            raise Exception("error")

        # Open the circuit
        try:
            await cb.call(fail)
        except Exception:
            pass

        # Wait and transition to half-open
        await asyncio.sleep(0.1)
        await cb._check_state()
        assert cb.state == CircuitState.HALF_OPEN

        # Failure should reopen circuit
        try:
            await cb.call(fail)
        except Exception:
            pass

        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerUsage:
    """Test different ways to use circuit breaker."""

    @pytest.mark.asyncio
    async def test_call_method(self):
        """Test using call() method."""
        cb = CircuitBreaker("test")

        async def async_func(x):
            return x * 2

        result = await cb.call(async_func, 21)
        assert result == 42

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using as context manager."""
        cb = CircuitBreaker("test")

        async with cb:
            result = 1 + 1

        assert result == 2
        assert cb.stats.successes == 1

    @pytest.mark.asyncio
    async def test_context_manager_records_failure(self):
        """Test context manager records failures."""
        cb = CircuitBreaker("test", failure_threshold=10)

        try:
            async with cb:
                raise ValueError("test error")
        except ValueError:
            pass

        assert cb.stats.failures == 1

    @pytest.mark.asyncio
    async def test_decorator(self):
        """Test using as decorator."""
        cb = CircuitBreaker("test")

        @cb.protect
        async def my_func(x):
            return x + 1

        result = await my_func(5)
        assert result == 6
        assert cb.stats.successes == 1

    @pytest.mark.asyncio
    async def test_sync_function_support(self):
        """Test circuit breaker works with sync functions."""
        cb = CircuitBreaker("test")

        def sync_func():
            return "sync result"

        result = await cb.call(sync_func)
        assert result == "sync result"


class TestCircuitBreakerExclusions:
    """Test excluded exceptions feature."""

    @pytest.mark.asyncio
    async def test_excluded_exceptions_not_counted(self):
        """Test excluded exceptions don't count as failures."""
        cb = CircuitBreaker(
            "test",
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )

        async def raise_value_error():
            raise ValueError("excluded")

        # These shouldn't count as failures
        for _ in range(5):
            try:
                await cb.call(raise_value_error)
            except ValueError:
                pass

        # Circuit should still be closed
        assert cb.state == CircuitState.CLOSED
        assert cb.stats.failures == 0

    @pytest.mark.asyncio
    async def test_non_excluded_exceptions_counted(self):
        """Test non-excluded exceptions are counted."""
        cb = CircuitBreaker(
            "test",
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )

        async def raise_runtime_error():
            raise RuntimeError("not excluded")

        # These should count as failures
        for _ in range(2):
            try:
                await cb.call(raise_runtime_error)
            except RuntimeError:
                pass

        # Circuit should be open
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerStats:
    """Test circuit breaker statistics."""

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        """Test statistics are tracked correctly."""
        cb = CircuitBreaker("test", failure_threshold=10)

        async def success():
            return True

        async def fail():
            raise Exception("error")

        # 3 successes
        for _ in range(3):
            await cb.call(success)

        # 2 failures
        for _ in range(2):
            try:
                await cb.call(fail)
            except Exception:
                pass

        assert cb.stats.successes == 3
        assert cb.stats.failures == 2
        assert cb.stats.total_requests == 5
        assert cb.stats.total_failures == 2

    @pytest.mark.asyncio
    async def test_to_dict_export(self):
        """Test circuit breaker state export."""
        cb = CircuitBreaker(
            "test_export",
            failure_threshold=5,
            recovery_timeout=30,
        )

        data = cb.to_dict()

        assert data["name"] == "test_export"
        assert data["state"] == "closed"
        assert "stats" in data
        assert "config" in data
        assert data["config"]["failure_threshold"] == 5
        assert data["config"]["recovery_timeout"] == 30

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test resetting circuit breaker."""
        cb = CircuitBreaker("test", failure_threshold=2)

        async def fail():
            raise Exception("error")

        # Open the circuit
        for _ in range(2):
            try:
                await cb.call(fail)
            except Exception:
                pass

        assert cb.state == CircuitState.OPEN

        # Reset
        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.stats.failures == 0
        assert cb.stats.successes == 0


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry."""

    def test_get_or_create(self):
        """Test getting or creating circuit breakers."""
        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("service1")
        cb2 = registry.get_or_create("service1")
        cb3 = registry.get_or_create("service2")

        assert cb1 is cb2  # Same instance
        assert cb1 is not cb3  # Different instance

    def test_get_nonexistent(self):
        """Test getting nonexistent circuit breaker."""
        registry = CircuitBreakerRegistry()

        result = registry.get("nonexistent")
        assert result is None

    def test_get_all_statuses(self):
        """Test getting all circuit breaker statuses."""
        registry = CircuitBreakerRegistry()

        registry.get_or_create("service1")
        registry.get_or_create("service2")

        statuses = registry.get_all_statuses()

        assert "service1" in statuses
        assert "service2" in statuses
        assert statuses["service1"]["state"] == "closed"

    def test_reset_all(self):
        """Test resetting all circuit breakers."""
        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("service1", failure_threshold=1)
        cb2 = registry.get_or_create("service2", failure_threshold=1)

        # Manually set states
        cb1._state = CircuitState.OPEN
        cb2._state = CircuitState.HALF_OPEN

        registry.reset_all()

        assert cb1.state == CircuitState.CLOSED
        assert cb2.state == CircuitState.CLOSED

    def test_custom_settings(self):
        """Test creating circuit breaker with custom settings."""
        registry = CircuitBreakerRegistry()

        cb = registry.get_or_create(
            "custom",
            failure_threshold=10,
            recovery_timeout=60,
        )

        assert cb.failure_threshold == 10
        assert cb.recovery_timeout == 60


class TestGlobalCircuitBreakers:
    """Test pre-configured global circuit breakers."""

    def test_get_redis_circuit(self):
        """Test Redis circuit breaker factory."""
        from src.infrastructure.circuit_breaker import get_redis_circuit

        cb = get_redis_circuit()
        assert cb.name == "redis"

    def test_get_postgres_circuit(self):
        """Test PostgreSQL circuit breaker factory."""
        from src.infrastructure.circuit_breaker import get_postgres_circuit

        cb = get_postgres_circuit()
        assert cb.name == "postgres"

    def test_get_llm_circuit(self):
        """Test LLM circuit breaker factory."""
        from src.infrastructure.circuit_breaker import get_llm_circuit

        cb = get_llm_circuit()
        assert cb.name == "llm"
        # LLM circuit should have custom settings
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 60


class TestCircuitBreakerConcurrency:
    """Test circuit breaker under concurrent usage."""

    @pytest.mark.asyncio
    async def test_concurrent_calls(self):
        """Test circuit breaker handles concurrent calls."""
        cb = CircuitBreaker("concurrent", failure_threshold=10)

        async def success():
            await asyncio.sleep(0.01)
            return True

        # Run many concurrent calls
        results = await asyncio.gather(*[cb.call(success) for _ in range(20)])

        assert all(results)
        assert cb.stats.successes == 20

    @pytest.mark.asyncio
    async def test_concurrent_failures(self):
        """Test circuit breaker opens correctly under concurrent failures."""
        cb = CircuitBreaker("concurrent_fail", failure_threshold=5)

        async def fail():
            await asyncio.sleep(0.01)
            raise Exception("error")

        # Run concurrent failing calls
        tasks = [cb.call(fail) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some should be regular exceptions, some should be CircuitBreakerError
        regular_errors = sum(1 for r in results if isinstance(r, Exception) and not isinstance(r, CircuitBreakerError))
        circuit_errors = sum(1 for r in results if isinstance(r, CircuitBreakerError))

        # Circuit should be open now
        assert cb.state == CircuitState.OPEN
