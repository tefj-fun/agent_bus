"""KAN-71: Job/task event stream endpoint with Redis pub/sub."""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional
import asyncio
import json
from datetime import datetime

from ...infrastructure.redis_client import redis_client

router = APIRouter(prefix="/events", tags=["events"])

EVENTS_CHANNEL = "agent_bus:events"


async def publish_event(event_type: str, data: dict) -> None:
    """Publish an event to Redis pub/sub.

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
        client = await redis_client.get_client()
        result = await client.publish(EVENTS_CHANNEL, json.dumps(event))
        print(f"[Events] Published {event_type} to {result} subscribers")
    except Exception as e:
        print(f"[Events] Failed to publish event: {e}")


async def event_generator(
    job_id: Optional[str] = None,
    event_types: Optional[list[str]] = None,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from Redis pub/sub.

    Args:
        job_id: Filter events by job ID
        event_types: Filter events by type

    Yields:
        SSE-formatted event strings
    """
    try:
        client = await redis_client.get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(EVENTS_CHANNEL)

        while True:
            try:
                # Get message with timeout for keepalive
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=30.0
                )

                if message is None:
                    # Send keepalive
                    yield ": keepalive\n\n"
                    continue

                if message["type"] == "message":
                    event = json.loads(message["data"])

                    # Apply filters
                    if job_id and event.get("data", {}).get("job_id") != job_id:
                        continue

                    if event_types and event.get("type") not in event_types:
                        continue

                    # Format as SSE
                    data = json.dumps(event)
                    yield f"data: {data}\n\n"

            except asyncio.TimeoutError:
                # Send keepalive on timeout
                yield ": keepalive\n\n"

    except asyncio.CancelledError:
        pass
    finally:
        try:
            await pubsub.unsubscribe(EVENTS_CHANNEL)
            await pubsub.close()
        except Exception:
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
    - `stage_started`: Workflow stage started
    - `stage_completed`: Workflow stage completed
    - `task_started`: Task execution started
    - `task_completed`: Task finished
    - `task_failed`: Task execution failed
    - `hitl_requested`: Human-in-the-loop intervention requested

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
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
async def get_event_history(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
) -> dict:
    """Get historical events (not real-time).

    Returns:
        Dictionary with events list
    """
    return {
        "events": [],
        "message": "Event history not yet implemented - use /stream for real-time events",
    }


# Helper functions for publishing common events

async def publish_job_created(job_id: str, project_id: str, **kwargs) -> None:
    """Publish job created event."""
    await publish_event("job_created", {"job_id": job_id, "project_id": project_id, **kwargs})


async def publish_job_started(job_id: str) -> None:
    """Publish job started event."""
    await publish_event("job_started", {"job_id": job_id})


async def publish_job_completed(job_id: str, result: dict = None) -> None:
    """Publish job completed event."""
    await publish_event("job_completed", {"job_id": job_id, "result": result or {}})


async def publish_job_failed(job_id: str, error: str) -> None:
    """Publish job failed event."""
    await publish_event("job_failed", {"job_id": job_id, "error": error})


async def publish_job_aborted(job_id: str, reason: str = "Aborted by user") -> None:
    """Publish job aborted event."""
    await publish_event("job_aborted", {"job_id": job_id, "reason": reason})


async def publish_stage_started(job_id: str, stage: str, agent: str = None) -> None:
    """Publish stage started event."""
    await publish_event("stage_started", {"job_id": job_id, "stage": stage, "agent": agent})


async def publish_stage_completed(job_id: str, stage: str) -> None:
    """Publish stage completed event."""
    await publish_event("stage_completed", {"job_id": job_id, "stage": stage})


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
