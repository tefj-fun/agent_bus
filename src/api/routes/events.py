"""KAN-71: Job/task event stream endpoint."""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional
import asyncio
import json
from datetime import datetime

router = APIRouter(prefix="/events", tags=["events"])


# In-memory event buffer (in production, use Redis Streams or Kafka)
event_buffer = asyncio.Queue(maxsize=1000)


async def publish_event(event_type: str, data: dict) -> None:
    """Publish an event to the stream.

    Args:
        event_type: Type of event (job_created, task_started, etc.)
        data: Event data
    """
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": event_type,
        "data": data,
    }

    try:
        event_buffer.put_nowait(event)
    except asyncio.QueueFull:
        # Drop oldest event if buffer is full
        try:
            event_buffer.get_nowait()
            event_buffer.put_nowait(event)
        except Exception:
            pass


async def event_generator(
    job_id: Optional[str] = None,
    event_types: Optional[list[str]] = None,
) -> AsyncGenerator[str, None]:
    """Generate SSE events.

    Args:
        job_id: Filter events by job ID
        event_types: Filter events by type

    Yields:
        SSE-formatted event strings
    """
    # Create a new queue for this client
    client_queue = asyncio.Queue(maxsize=100)

    # Subscribe to events (simplified - in production use pub/sub)
    try:
        while True:
            try:
                # Get event with timeout
                event = await asyncio.wait_for(event_buffer.get(), timeout=30.0)

                # Apply filters
                if job_id and event.get("data", {}).get("job_id") != job_id:
                    continue

                if event_types and event.get("type") not in event_types:
                    continue

                # Format as SSE
                data = json.dumps(event)
                yield f"data: {data}\n\n"

            except asyncio.TimeoutError:
                # Send keepalive
                yield f": keepalive\n\n"

    except asyncio.CancelledError:
        # Client disconnected
        pass


@router.get("/stream")
async def stream_events(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    event_types: Optional[str] = Query(None, description="Comma-separated event types"),
) -> StreamingResponse:
    """Stream job and task events in real-time using Server-Sent Events (SSE).

    This endpoint provides a real-time stream of events for monitoring
    job and task execution progress.

    **Event Types:**
    - `job_created`: New job submitted
    - `job_started`: Job execution started
    - `job_completed`: Job finished successfully
    - `job_failed`: Job execution failed
    - `task_started`: Task execution started
    - `task_completed`: Task finished
    - `task_failed`: Task execution failed
    - `hitl_requested`: Human-in-the-loop intervention requested

    **Example:**
    ```python
    import requests

    with requests.get('http://localhost:8000/events/stream', stream=True) as r:
        for line in r.iter_lines():
            if line.startswith(b'data:'):
                event = json.loads(line[5:])
                print(event)
    ```

    Args:
        job_id: Optional job ID to filter events
        event_types: Optional comma-separated list of event types to include

    Returns:
        StreamingResponse with text/event-stream content type
    """
    # Parse event types
    types = None
    if event_types:
        types = [t.strip() for t in event_types.split(",")]

    return StreamingResponse(
        event_generator(job_id=job_id, event_types=types),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/history")
async def get_event_history(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
) -> dict:
    """Get historical events (not real-time).

    This is a placeholder that would query a persistent event store
    (e.g., PostgreSQL, Elasticsearch) in production.

    Args:
        job_id: Optional job ID filter
        limit: Maximum number of events

    Returns:
        Dictionary with events list
    """
    return {
        "events": [],
        "message": "Event history not yet implemented - use /stream for real-time events",
    }


# Helper functions for publishing common events

async def publish_job_created(job_id: str, job_data: dict) -> None:
    """Publish job created event."""
    await publish_event("job_created", {"job_id": job_id, **job_data})


async def publish_job_started(job_id: str) -> None:
    """Publish job started event."""
    await publish_event("job_started", {"job_id": job_id})


async def publish_job_completed(job_id: str, result: dict) -> None:
    """Publish job completed event."""
    await publish_event("job_completed", {"job_id": job_id, "result": result})


async def publish_job_failed(job_id: str, error: str) -> None:
    """Publish job failed event."""
    await publish_event("job_failed", {"job_id": job_id, "error": error})


async def publish_task_started(job_id: str, task_id: str) -> None:
    """Publish task started event."""
    await publish_event("task_started", {"job_id": job_id, "task_id": task_id})


async def publish_task_completed(job_id: str, task_id: str) -> None:
    """Publish task completed event."""
    await publish_event("task_completed", {"job_id": job_id, "task_id": task_id})


async def publish_hitl_requested(job_id: str, task_id: str, reason: str) -> None:
    """Publish HITL requested event."""
    await publish_event(
        "hitl_requested",
        {"job_id": job_id, "task_id": task_id, "reason": reason}
    )
