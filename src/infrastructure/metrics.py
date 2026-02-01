"""Prometheus metrics for agent_bus."""
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Callable

# Application info
app_info = Info('agent_bus_app', 'Application information')
app_info.info({
    'version': '1.0.0',
    'environment': 'production'
})

# API metrics
http_requests_total = Counter(
    'agent_bus_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'agent_bus_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# Job metrics
jobs_created_total = Counter(
    'agent_bus_jobs_created_total',
    'Total jobs created',
    ['project_type']
)

jobs_completed_total = Counter(
    'agent_bus_jobs_completed_total',
    'Total jobs completed',
    ['status']
)

jobs_active = Gauge(
    'agent_bus_jobs_active',
    'Currently active jobs'
)

job_duration_seconds = Histogram(
    'agent_bus_job_duration_seconds',
    'Job execution duration in seconds',
    ['stage'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)
)

# Agent metrics
agent_executions_total = Counter(
    'agent_bus_agent_executions_total',
    'Total agent executions',
    ['agent_type', 'status']
)

agent_execution_duration_seconds = Histogram(
    'agent_bus_agent_execution_duration_seconds',
    'Agent execution duration in seconds',
    ['agent_type'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

agent_llm_calls_total = Counter(
    'agent_bus_agent_llm_calls_total',
    'Total LLM API calls',
    ['agent_type', 'provider']
)

agent_llm_tokens_total = Counter(
    'agent_bus_agent_llm_tokens_total',
    'Total LLM tokens consumed',
    ['agent_type', 'provider', 'type']  # type: input/output
)

# Worker metrics
worker_tasks_processed = Counter(
    'agent_bus_worker_tasks_processed_total',
    'Total tasks processed by workers',
    ['worker_type', 'status']
)

worker_queue_size = Gauge(
    'agent_bus_worker_queue_size',
    'Current worker queue size',
    ['queue_name']
)

# Database metrics
db_connections_active = Gauge(
    'agent_bus_db_connections_active',
    'Active database connections'
)

db_query_duration_seconds = Histogram(
    'agent_bus_db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# Memory system metrics
memory_queries_total = Counter(
    'agent_bus_memory_queries_total',
    'Total memory system queries',
    ['pattern_type']
)

memory_hits_total = Counter(
    'agent_bus_memory_hits_total',
    'Total memory hits',
    ['pattern_type']
)

memory_store_size = Gauge(
    'agent_bus_memory_store_size',
    'Number of documents in memory store'
)

# Redis metrics
redis_operations_total = Counter(
    'agent_bus_redis_operations_total',
    'Total Redis operations',
    ['operation', 'status']
)

# Error metrics
errors_total = Counter(
    'agent_bus_errors_total',
    'Total errors',
    ['error_type', 'component']
)


def track_execution_time(metric: Histogram, labels: dict = None):
    """Decorator to track function execution time."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
                raise
        
        if hasattr(func, '__await__'):
            return async_wrapper
        return sync_wrapper
    
    return decorator
