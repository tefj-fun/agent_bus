"""Prometheus Metrics Module.

Provides comprehensive metrics collection for Agent Bus system.
"""
import time
from typing import Dict, Optional
from functools import wraps
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

# ============================================================================
# Project Metrics
# ============================================================================

projects_total = Counter(
    "agent_bus_projects_total",
    "Total number of projects created",
    ["status"],
)

projects_by_stage = Gauge(
    "agent_bus_projects_by_stage",
    "Number of projects in each stage",
    ["stage"],
)

stage_duration_seconds = Histogram(
    "agent_bus_stage_duration_seconds",
    "Time taken to complete each stage",
    ["stage"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
)

# ============================================================================
# Agent Metrics
# ============================================================================

agent_invocations_total = Counter(
    "agent_bus_agent_invocations_total",
    "Total number of agent invocations",
    ["agent_type", "status"],
)

agent_duration_seconds = Histogram(
    "agent_bus_agent_duration_seconds",
    "Time taken for agent execution",
    ["agent_type"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120),
)

# ============================================================================
# LLM Metrics
# ============================================================================

llm_tokens_total = Counter(
    "agent_bus_llm_tokens_total",
    "Total LLM tokens consumed",
    ["model", "type"],  # type: prompt, completion
)

llm_requests_total = Counter(
    "agent_bus_llm_requests_total",
    "Total LLM API requests",
    ["model", "status"],
)

llm_cost_dollars = Counter(
    "agent_bus_llm_cost_dollars",
    "Estimated LLM cost in dollars",
    ["model"],
)

llm_request_duration_seconds = Histogram(
    "agent_bus_llm_request_duration_seconds",
    "LLM API request duration",
    ["model"],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60),
)

# ============================================================================
# System Metrics
# ============================================================================

errors_total = Counter(
    "agent_bus_errors_total",
    "Total errors by type",
    ["error_type", "component"],
)

redis_queue_depth = Gauge(
    "agent_bus_redis_queue_depth",
    "Number of tasks in Redis queue",
    ["queue_name"],
)

worker_active_tasks = Gauge(
    "agent_bus_worker_active_tasks",
    "Number of active tasks per worker",
    ["worker_id", "worker_type"],
)

database_connections = Gauge(
    "agent_bus_database_connections",
    "Number of active database connections",
)

# ============================================================================
# HITL Metrics
# ============================================================================

hitl_approvals_total = Counter(
    "agent_bus_hitl_approvals_total",
    "Total HITL approval actions",
    ["stage", "action"],  # action: approved, rejected, modified
)

hitl_wait_time_seconds = Histogram(
    "agent_bus_hitl_wait_time_seconds",
    "Time waiting for human approval",
    ["stage"],
    buckets=(60, 300, 900, 1800, 3600, 7200, 14400, 28800),
)

# ============================================================================
# Memory System Metrics
# ============================================================================

memory_queries_total = Counter(
    "agent_bus_memory_queries_total",
    "Total memory system queries",
    ["query_type"],
)

memory_hits_total = Counter(
    "agent_bus_memory_hits_total",
    "Total memory retrieval hits",
    ["collection"],
)

memory_storage_size_bytes = Gauge(
    "agent_bus_memory_storage_size_bytes",
    "Memory system storage size",
)

# ============================================================================
# Skills System Metrics
# ============================================================================

skills_loaded = Gauge(
    "agent_bus_skills_loaded",
    "Number of loaded skills",
)

skills_invocations_total = Counter(
    "agent_bus_skills_invocations_total",
    "Total skill invocations",
    ["skill_name", "agent_type"],
)

# ============================================================================
# System Info
# ============================================================================

system_info = Info(
    "agent_bus_system_info",
    "Agent Bus system information",
)

# ============================================================================
# Metric Helper Functions
# ============================================================================


def record_project_created(status: str = "created"):
    """Record a new project creation."""
    projects_total.labels(status=status).inc()


def record_project_stage(stage: str, count: int):
    """Update project count for a stage."""
    projects_by_stage.labels(stage=stage).set(count)


def record_stage_duration(stage: str, duration: float):
    """Record stage completion duration."""
    stage_duration_seconds.labels(stage=stage).observe(duration)


def record_agent_invocation(agent_type: str, status: str = "success", duration: Optional[float] = None):
    """Record an agent invocation."""
    agent_invocations_total.labels(agent_type=agent_type, status=status).inc()
    if duration is not None:
        agent_duration_seconds.labels(agent_type=agent_type).observe(duration)


def record_llm_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration: float,
    cost: float = 0.0,
    status: str = "success",
):
    """Record LLM API usage."""
    llm_tokens_total.labels(model=model, type="prompt").inc(prompt_tokens)
    llm_tokens_total.labels(model=model, type="completion").inc(completion_tokens)
    llm_requests_total.labels(model=model, status=status).inc()
    llm_request_duration_seconds.labels(model=model).observe(duration)
    if cost > 0:
        llm_cost_dollars.labels(model=model).inc(cost)


def record_error(error_type: str, component: str):
    """Record an error."""
    errors_total.labels(error_type=error_type, component=component).inc()


def update_queue_depth(queue_name: str, depth: int):
    """Update Redis queue depth."""
    redis_queue_depth.labels(queue_name=queue_name).set(depth)


def update_worker_tasks(worker_id: str, worker_type: str, task_count: int):
    """Update worker active task count."""
    worker_active_tasks.labels(worker_id=worker_id, worker_type=worker_type).set(task_count)


def update_db_connections(count: int):
    """Update database connection count."""
    database_connections.set(count)


def record_hitl_action(stage: str, action: str, wait_time: Optional[float] = None):
    """Record HITL approval action."""
    hitl_approvals_total.labels(stage=stage, action=action).inc()
    if wait_time is not None:
        hitl_wait_time_seconds.labels(stage=stage).observe(wait_time)


def record_memory_query(query_type: str):
    """Record memory system query."""
    memory_queries_total.labels(query_type=query_type).inc()


def record_memory_hit(collection: str):
    """Record memory retrieval hit."""
    memory_hits_total.labels(collection=collection).inc()


def update_memory_storage(size_bytes: int):
    """Update memory storage size."""
    memory_storage_size_bytes.set(size_bytes)


def update_skills_count(count: int):
    """Update loaded skills count."""
    skills_loaded.set(count)


def record_skill_invocation(skill_name: str, agent_type: str):
    """Record skill invocation."""
    skills_invocations_total.labels(skill_name=skill_name, agent_type=agent_type).inc()


def set_system_info(version: str, environment: str, **kwargs):
    """Set system information."""
    info_dict = {
        "version": version,
        "environment": environment,
        **kwargs,
    }
    system_info.info(info_dict)


# ============================================================================
# Decorators
# ============================================================================


def track_agent_execution(agent_type: str):
    """Decorator to track agent execution metrics."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                record_error(type(e).__name__, agent_type)
                raise
            finally:
                duration = time.time() - start_time
                record_agent_invocation(agent_type, status, duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                record_error(type(e).__name__, agent_type)
                raise
            finally:
                duration = time.time() - start_time
                record_agent_invocation(agent_type, status, duration)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def track_llm_request(model: str):
    """Decorator to track LLM request metrics."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                # Extract token usage from result if available
                if isinstance(result, dict):
                    usage = result.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    if prompt_tokens or completion_tokens:
                        duration = time.time() - start_time
                        record_llm_usage(
                            model, prompt_tokens, completion_tokens, duration
                        )
                return result
            except Exception as e:
                status = "error"
                record_error(type(e).__name__, "llm")
                raise
            finally:
                if status == "error":
                    duration = time.time() - start_time
                    llm_requests_total.labels(model=model, status=status).inc()
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = func(*args, **kwargs)
                if isinstance(result, dict):
                    usage = result.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    if prompt_tokens or completion_tokens:
                        duration = time.time() - start_time
                        record_llm_usage(
                            model, prompt_tokens, completion_tokens, duration
                        )
                return result
            except Exception as e:
                status = "error"
                record_error(type(e).__name__, "llm")
                raise
            finally:
                if status == "error":
                    duration = time.time() - start_time
                    llm_requests_total.labels(model=model, status=status).inc()
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# ============================================================================
# Metrics Endpoint
# ============================================================================


def get_metrics() -> bytes:
    """Get Prometheus metrics in exposition format."""
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Get content type for metrics response."""
    return CONTENT_TYPE_LATEST
