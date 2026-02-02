"""Infrastructure module for agent_bus.

This module provides:
- DI Container for dependency management
- Circuit breakers for resilience
- Database and cache clients
"""

from .container import Container, container, get_redis, get_postgres_pool, get_anthropic
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitState,
    circuit_registry,
    get_redis_circuit,
    get_postgres_circuit,
    get_llm_circuit,
)
from .redis_client import RedisClient, redis_client
from .postgres_client import PostgresClient, postgres_client

__all__ = [
    # Container
    "Container",
    "container",
    "get_redis",
    "get_postgres_pool",
    "get_anthropic",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitBreakerRegistry",
    "CircuitState",
    "circuit_registry",
    "get_redis_circuit",
    "get_postgres_circuit",
    "get_llm_circuit",
    # Legacy clients
    "RedisClient",
    "redis_client",
    "PostgresClient",
    "postgres_client",
]
