"""KAN-71: Job/task event stream endpoint with Redis pub/sub."""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Optional
import asyncio
import json
from datetime import datetime

from ...infrastructure.redis_client import redis_client
from ...infrastructure.postgres_client import postgres_client

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

    # Best-effort persistence for history
    try:
        job_id = data.get("job_id") if isinstance(data, dict) else None
        if job_id:
            agent_id = data.get("agent") or data.get("agent_id") or "system"
            message = data.get("message") or _default_event_message(event_type, data)
            pool = await postgres_client.get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO agent_events (agent_id, job_id, event_type, message, data)
                    VALUES ($1, $2, $3, $4, $5::jsonb)
                    """,
                    agent_id,
                    job_id,
                    event_type,
                    message,
                    json.dumps(data or {}),
                )
    except Exception:
        # Never break event publishing if persistence fails
        pass


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
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            if job_id:
                rows = await conn.fetch(
                    """
                    SELECT id, agent_id, job_id, event_type, message, data, created_at
                    FROM agent_events
                    WHERE job_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    job_id,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, agent_id, job_id, event_type, message, data, created_at
                    FROM agent_events
                    ORDER BY created_at DESC
                    LIMIT $1
                    """,
                    limit,
                )

            events = []
            has_stage_events = False
            for row in rows:
                data = row.get("data") or {}
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except Exception:
                        data = {}
                event_type = row.get("event_type") or "agent_event"
                if event_type.startswith("stage_"):
                    has_stage_events = True
                events.append(
                    {
                        "id": str(row.get("id") or ""),
                        "type": event_type,
                        "message": row.get("message") or "",
                        "timestamp": row.get("created_at").isoformat()
                        if row.get("created_at")
                        else "",
                        "agent": row.get("agent_id"),
                        "job_id": row.get("job_id"),
                        "metadata": data,
                    }
                )

            # Synthesize stage events from tasks when none were persisted
            if job_id and not has_stage_events:
                task_rows = await conn.fetch(
                    """
                    SELECT task_type, status, created_at, completed_at
                    FROM tasks
                    WHERE job_id = $1
                    ORDER BY created_at ASC
                    """,
                    job_id,
                )
                synthetic = []
                for task in task_rows:
                    stage = task.get("task_type")
                    if not stage:
                        continue
                    created_at = task.get("created_at")
                    completed_at = task.get("completed_at")
                    if created_at:
                        synthetic.append(
                            {
                                "id": f"synth-start-{stage}-{created_at.timestamp()}",
                                "type": "stage_started",
                                "message": f"Stage started: {stage}",
                                "timestamp": created_at.isoformat(),
                                "agent": None,
                                "job_id": job_id,
                                "metadata": {"stage": stage},
                            }
                        )
                    if completed_at:
                        synthetic.append(
                            {
                                "id": f"synth-done-{stage}-{completed_at.timestamp()}",
                                "type": "stage_completed",
                                "message": f"Stage completed: {stage}",
                                "timestamp": completed_at.isoformat(),
                                "agent": None,
                                "job_id": job_id,
                                "metadata": {"stage": stage},
                            }
                        )

                events.extend(synthetic)

            # Sort newest first
            events = sorted(
                events,
                key=lambda e: e.get("timestamp") or "",
                reverse=True,
            )

        return {"events": events[:limit]}
    except Exception as e:
        return {"events": [], "message": f"Failed to load event history: {e}"}


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


def _default_event_message(event_type: str, data: dict) -> str:
    if event_type == "stage_started":
        return f"Stage started: {data.get('stage', '')}".strip()
    if event_type == "stage_completed":
        return f"Stage completed: {data.get('stage', '')}".strip()
    if event_type == "task_started":
        return f"Task started: {data.get('task_id', '')}".strip()
    if event_type == "task_completed":
        return f"Task completed: {data.get('task_id', '')}".strip()
    if event_type == "job_started":
        return "Job started"
    if event_type == "job_completed":
        return "Job completed"
    if event_type == "job_failed":
        return f"Job failed: {data.get('error', '')}".strip()
    if event_type == "hitl_requested":
        return f"Approval requested: {data.get('reason', '')}".strip()
    return event_type.replace("_", " ").title()
