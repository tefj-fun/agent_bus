"""API routes for project management."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...infrastructure.postgres_client import postgres_client


router = APIRouter()


class ProjectRequest(BaseModel):
    """Request model for creating a project."""

    project_id: str
    requirements: str
    metadata: Optional[dict] = None


class ProjectResponse(BaseModel):
    """Response model for project creation."""

    job_id: str
    project_id: str
    status: str
    message: str


@router.post("/", response_model=ProjectResponse)
async def create_project(request: ProjectRequest):
    """
    Create a new project and start the SWE workflow.

    Args:
        request: Project creation request

    Returns:
        Project response with job ID
    """
    try:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        await postgres_client.create_job(
            job_id=job_id,
            project_id=request.project_id,
            status="queued",
            workflow_stage="initialization"
        )

        # Persist requirements for the orchestrator service
        await postgres_client.update_job_metadata(
            job_id=job_id,
            metadata={
                "requirements": request.requirements,
                "project_metadata": request.metadata or {},
            },
        )

        return ProjectResponse(
            job_id=job_id,
            project_id=request.project_id,
            status="queued",
            message="Project workflow queued"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a job.

    Args:
        job_id: Job identifier

    Returns:
        Job status and details
    """
    try:
        # Query database for job status
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, project_id, status, workflow_stage, created_at, updated_at,
                       completed_at, metadata
                FROM jobs
                WHERE id = $1
                """,
                job_id
            )

            if not row:
                raise HTTPException(status_code=404, detail="Job not found")

            job = dict(row)

            task_row = await conn.fetchrow(
                """
                SELECT id, status, task_type, completed_at
                FROM tasks
                WHERE job_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                job_id
            )
            if task_row:
                job["latest_task"] = dict(task_row)

            return job

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/prd")
async def get_job_prd(job_id: str):
    """Fetch the latest PRD for a job."""
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            artifact_row = await conn.fetchrow(
                """
                SELECT id, content, metadata, updated_at, created_at
                FROM artifacts
                WHERE job_id = $1 AND type = 'prd'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id
            )
            if artifact_row:
                return dict(artifact_row)

            task_row = await conn.fetchrow(
                """
                SELECT id, output_data->>'prd_content' AS prd_content,
                       output_data, completed_at, created_at
                FROM tasks
                WHERE job_id = $1 AND task_type = 'prd_generation'
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id
            )
            if task_row and task_row.get("prd_content"):
                payload = dict(task_row)
                payload["content"] = payload.pop("prd_content")
                return payload

        raise HTTPException(status_code=404, detail="PRD not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/plan")
async def get_job_plan(job_id: str):
    """Fetch the latest plan for a job."""
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            artifact_row = await conn.fetchrow(
                """
                SELECT id, content, metadata, updated_at, created_at
                FROM artifacts
                WHERE job_id = $1 AND type = 'plan'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id
            )
            if artifact_row:
                return dict(artifact_row)

            task_row = await conn.fetchrow(
                """
                SELECT id, output_data->'plan' AS plan,
                       output_data, completed_at, created_at
                FROM tasks
                WHERE job_id = $1 AND task_type = 'plan_generation'
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id
            )
            if task_row and task_row.get("plan"):
                payload = dict(task_row)
                payload["content"] = payload.pop("plan")
                return payload

        raise HTTPException(status_code=404, detail="Plan not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/architecture")
async def get_job_architecture(job_id: str):
    """Fetch the latest architecture for a job."""
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            artifact_row = await conn.fetchrow(
                """
                SELECT id, content, metadata, updated_at, created_at
                FROM artifacts
                WHERE job_id = $1 AND type = 'architecture'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id
            )
            if artifact_row:
                return dict(artifact_row)

            task_row = await conn.fetchrow(
                """
                SELECT id, output_data->'architecture' AS architecture,
                       output_data, completed_at, created_at
                FROM tasks
                WHERE job_id = $1 AND task_type = 'architecture_design'
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id
            )
            if task_row and task_row.get("architecture"):
                payload = dict(task_row)
                payload["content"] = payload.pop("architecture")
                return payload

        raise HTTPException(status_code=404, detail="Architecture not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/ui_ux")
async def get_job_ui_ux(job_id: str):
    """Fetch the latest UI/UX design for a job."""
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            artifact_row = await conn.fetchrow(
                """
                SELECT id, content, metadata, updated_at, created_at
                FROM artifacts
                WHERE job_id = $1 AND type = 'ui_ux'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id
            )
            if artifact_row:
                return dict(artifact_row)

            task_row = await conn.fetchrow(
                """
                SELECT id, output_data->'ui_ux' AS ui_ux,
                       output_data, completed_at, created_at
                FROM tasks
                WHERE job_id = $1 AND task_type = 'uiux_design'
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id
            )
            if task_row and task_row.get("ui_ux"):
                payload = dict(task_row)
                payload["content"] = payload.pop("ui_ux")
                return payload

        raise HTTPException(status_code=404, detail="UI/UX design not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/development")
async def get_job_development(job_id: str):
    """Fetch the latest development plan for a job."""
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            artifact_row = await conn.fetchrow(
                """
                SELECT id, content, metadata, updated_at, created_at
                FROM artifacts
                WHERE job_id = $1 AND type = 'development'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id
            )
            if artifact_row:
                return dict(artifact_row)

            task_row = await conn.fetchrow(
                """
                SELECT id, output_data->'development' AS development,
                       output_data, completed_at, created_at
                FROM tasks
                WHERE job_id = $1 AND task_type = 'development'
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id
            )
            if task_row and task_row.get("development"):
                payload = dict(task_row)
                payload["content"] = payload.pop("development")
                return payload

        raise HTTPException(status_code=404, detail="Development plan not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/memory_hits")
async def get_job_memory_hits(job_id: str):
    """Return memory hits captured during PRD generation."""
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            task_row = await conn.fetchrow(
                """
                SELECT output_data->'memory_hits' AS memory_hits,
                       metadata->'memory_hits' AS metadata_hits
                FROM tasks
                WHERE job_id = $1 AND task_type = 'prd_generation'
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id
            )

        if not task_row:
            raise HTTPException(status_code=404, detail="Memory hits not found")

        hits = task_row.get("memory_hits") or task_row.get("metadata_hits") or []

        # Normalize hits to a JSON array (some historical rows stored a JSON-encoded string)
        if isinstance(hits, str):
            import json
            try:
                hits = json.loads(hits)
            except Exception:
                hits = []

        if hits is None:
            hits = []

        return {"job_id": job_id, "memory_hits": hits}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ApprovalRequest(BaseModel):
    """Request model for approval actions."""

    notes: Optional[str] = None


@router.post("/{job_id}/approve")
async def approve_job(job_id: str, request: ApprovalRequest):
    """Approve a job after PRD generation.

    Note: continuation is handled by the orchestrator service (not the API process).
    """
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            exists = await conn.fetchval("SELECT 1 FROM jobs WHERE id = $1", job_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Job not found")

        await postgres_client.update_job_status(
            job_id=job_id,
            status="approved",
            workflow_stage="plan_generation"
        )
        await postgres_client.update_job_metadata(
            job_id=job_id,
            metadata={
                "approval_notes": request.notes,
                "approved_at": datetime.now(timezone.utc).isoformat()
            }
        )

        return {"job_id": job_id, "status": "approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/request_changes")
async def request_changes(job_id: str, request: ApprovalRequest):
    """Request changes after PRD generation."""
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            exists = await conn.fetchval("SELECT 1 FROM jobs WHERE id = $1", job_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Job not found")

        await postgres_client.update_job_status(
            job_id=job_id,
            status="changes_requested",
            workflow_stage="waiting_for_approval"
        )
        await postgres_client.update_job_metadata(
            job_id=job_id,
            metadata={
                "change_request_notes": request.notes,
                "changes_requested_at": datetime.now(timezone.utc).isoformat()
            }
        )
        return {"job_id": job_id, "status": "changes_requested"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
