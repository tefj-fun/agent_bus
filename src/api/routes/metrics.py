"""KAN-72: Metrics endpoint (basic)."""

from fastapi import APIRouter
from typing import Dict, Any
import time
import psutil

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Simple metrics storage (in production, use Prometheus client library)
_metrics = {
    "requests_total": 0,
    "requests_success": 0,
    "requests_error": 0,
    "jobs_submitted": 0,
    "jobs_completed": 0,
    "jobs_failed": 0,
    "tasks_executed": 0,
    "gpu_tasks_executed": 0,
    "cpu_tasks_executed": 0,
}

_start_time = time.time()


def increment_metric(name: str, value: int = 1) -> None:
    """Increment a metric counter.

    Args:
        name: Metric name
        value: Amount to increment by
    """
    if name in _metrics:
        _metrics[name] += value


@router.get("")
async def get_metrics() -> Dict[str, Any]:
    """Get basic application metrics.

    Returns metrics in a simple JSON format. In production, this would
    typically return Prometheus-compatible metrics via /metrics endpoint.

    **Metrics Included:**
    - Request counts (total, success, error)
    - Job counts (submitted, completed, failed)
    - Task execution counts (total, GPU, CPU)
    - System metrics (CPU, memory, uptime)

    Returns:
        Dictionary with all metrics
    """
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    uptime_seconds = time.time() - _start_time

    return {
        "counters": _metrics,
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_bytes": memory.used,
            "memory_total_bytes": memory.total,
            "uptime_seconds": uptime_seconds,
        },
        "timestamp": time.time(),
    }


@router.get("/prometheus")
async def get_prometheus_metrics() -> str:
    """Get metrics in Prometheus exposition format.

    Returns:
        Prometheus-formatted metrics as text
    """
    lines = []

    # Counter metrics
    for name, value in _metrics.items():
        lines.append(f"# TYPE agent_bus_{name} counter")
        lines.append(f"agent_bus_{name} {value}")

    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    uptime = time.time() - _start_time

    lines.append("# TYPE agent_bus_cpu_percent gauge")
    lines.append(f"agent_bus_cpu_percent {cpu_percent}")

    lines.append("# TYPE agent_bus_memory_percent gauge")
    lines.append(f"agent_bus_memory_percent {memory.percent}")

    lines.append("# TYPE agent_bus_uptime_seconds gauge")
    lines.append(f"agent_bus_uptime_seconds {uptime}")

    return "\n".join(lines) + "\n"


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Simple health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "uptime_seconds": time.time() - _start_time,
        "timestamp": time.time(),
    }


@router.post("/reset")
async def reset_metrics() -> Dict[str, str]:
    """Reset all metrics counters (for testing).

    Returns:
        Confirmation message
    """
    global _metrics
    _metrics = {key: 0 for key in _metrics}
    return {"message": "Metrics reset successfully"}
