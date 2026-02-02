"""Circuit Breaker implementation for resilient service calls.

The circuit breaker pattern prevents cascading failures by:
1. Tracking failures in external service calls
2. "Opening" the circuit after too many failures (fast-fail)
3. Periodically testing if the service has recovered
4. "Closing" the circuit when the service is healthy again
"""

from __future__ import annotations

import asyncio
import functools
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

from ..config import settings


T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests flow through
    OPEN = "open"  # Circuit tripped, requests fail immediately
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""

    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    total_requests: int = 0
    total_failures: int = 0
    circuit_opened_count: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, circuit_name: str, recovery_time: float):
        self.circuit_name = circuit_name
        self.recovery_time = recovery_time
        super().__init__(
            f"Circuit '{circuit_name}' is open. "
            f"Retry after {recovery_time:.1f} seconds."
        )


class CircuitBreaker(Generic[T]):
    """
    Circuit Breaker for protecting external service calls.

    Usage:
        # Create a circuit breaker
        cb = CircuitBreaker("redis")

        # Use as context manager
        async with cb:
            await redis.ping()

        # Or use the call method
        result = await cb.call(redis.ping)

        # Or use as decorator
        @cb.protect
        async def fetch_data():
            ...
    """

    def __init__(
        self,
        name: str,
        failure_threshold: Optional[int] = None,
        recovery_timeout: Optional[int] = None,
        half_open_requests: Optional[int] = None,
        excluded_exceptions: tuple = (),
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for this circuit
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before testing recovery
            half_open_requests: Number of test requests in half-open state
            excluded_exceptions: Exceptions that don't count as failures
        """
        self.name = name
        self.failure_threshold = (
            failure_threshold or settings.circuit_breaker_failure_threshold
        )
        self.recovery_timeout = (
            recovery_timeout or settings.circuit_breaker_recovery_timeout
        )
        self.half_open_requests = (
            half_open_requests or settings.circuit_breaker_half_open_requests
        )
        self.excluded_exceptions = excluded_exceptions

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_successes = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get circuit statistics."""
        return self._stats

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try resetting the circuit."""
        if self._stats.last_failure_time is None:
            return True
        elapsed = time.time() - self._stats.last_failure_time
        return elapsed >= self.recovery_timeout

    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._stats.successes += 1
            self._stats.total_requests += 1
            self._stats.last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.half_open_requests:
                    # Service recovered, close the circuit
                    self._state = CircuitState.CLOSED
                    self._stats.failures = 0
                    self._half_open_successes = 0

    async def _record_failure(self, error: Exception) -> None:
        """Record a failed call."""
        async with self._lock:
            self._stats.failures += 1
            self._stats.total_failures += 1
            self._stats.total_requests += 1
            self._stats.last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Recovery failed, reopen circuit
                self._state = CircuitState.OPEN
                self._half_open_successes = 0
            elif (
                self._state == CircuitState.CLOSED
                and self._stats.failures >= self.failure_threshold
            ):
                # Too many failures, open circuit
                self._state = CircuitState.OPEN
                self._stats.circuit_opened_count += 1

    async def _check_state(self) -> None:
        """Check and potentially transition circuit state."""
        async with self._lock:
            if self._state == CircuitState.OPEN and self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._half_open_successes = 0

    async def __aenter__(self) -> "CircuitBreaker":
        """Enter the circuit breaker context."""
        await self._check_state()

        if self._state == CircuitState.OPEN:
            recovery_time = self.recovery_timeout - (
                time.time() - (self._stats.last_failure_time or 0)
            )
            raise CircuitBreakerError(self.name, max(0, recovery_time))

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit the circuit breaker context."""
        if exc_type is None:
            await self._record_success()
        elif not isinstance(exc_val, self.excluded_exceptions):
            await self._record_failure(exc_val)
        return False  # Don't suppress exceptions

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Function to call (can be sync or async)
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self:
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result

    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to protect a function with the circuit breaker.

        Usage:
            @circuit_breaker.protect
            async def fetch_from_api():
                ...
        """

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await self.call(func, *args, **kwargs)

        return wrapper

    def reset(self) -> None:
        """Reset the circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_successes = 0

    def to_dict(self) -> Dict[str, Any]:
        """Export circuit breaker state as dictionary."""
        return {
            "name": self.name,
            "state": self._state.value,
            "stats": {
                "failures": self._stats.failures,
                "successes": self._stats.successes,
                "total_requests": self._stats.total_requests,
                "total_failures": self._stats.total_failures,
                "circuit_opened_count": self._stats.circuit_opened_count,
            },
            "config": {
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "half_open_requests": self.half_open_requests,
            },
        }


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Usage:
        registry = CircuitBreakerRegistry()
        redis_cb = registry.get_or_create("redis")
        postgres_cb = registry.get_or_create("postgres")

        # Get all circuit statuses
        statuses = registry.get_all_statuses()
    """

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    def get_or_create(
        self,
        name: str,
        failure_threshold: Optional[int] = None,
        recovery_timeout: Optional[int] = None,
        **kwargs,
    ) -> CircuitBreaker:
        """
        Get existing circuit breaker or create new one.

        Args:
            name: Circuit breaker identifier
            failure_threshold: Optional custom threshold
            recovery_timeout: Optional custom timeout
            **kwargs: Additional CircuitBreaker arguments

        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                **kwargs,
            )
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by name."""
        return self._breakers.get(name)

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {name: cb.to_dict() for name, cb in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for cb in self._breakers.values():
            cb.reset()


# Global registry
circuit_registry = CircuitBreakerRegistry()


# Pre-configured circuit breakers for common services
def get_redis_circuit() -> CircuitBreaker:
    """Get circuit breaker for Redis operations."""
    return circuit_registry.get_or_create("redis")


def get_postgres_circuit() -> CircuitBreaker:
    """Get circuit breaker for PostgreSQL operations."""
    return circuit_registry.get_or_create("postgres")


def get_llm_circuit() -> CircuitBreaker:
    """Get circuit breaker for LLM API calls."""
    return circuit_registry.get_or_create(
        "llm",
        failure_threshold=3,  # LLM failures are more expensive
        recovery_timeout=60,  # Wait longer before retrying LLM
    )
