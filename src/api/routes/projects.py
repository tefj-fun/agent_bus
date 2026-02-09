"""API routes for project management."""

import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from ...infrastructure.postgres_client import postgres_client
from ...config import settings
from ...storage.artifact_store import get_artifact_store, FileArtifactStore
from ...utils.truth import hash_text
from .events import publish_job_aborted
from ...orchestration.workflow import WorkflowStage
from .artifacts import export_job_artifacts as export_job_artifacts_handler


async def _get_artifact_from_file_store(job_id: str, artifact_type: str) -> Optional[dict]:
    """Try to get artifact from file storage.

    Returns artifact dict if found, None otherwise.
    """
    if settings.artifact_storage_backend != "file":
        return None

    try:
        store = get_artifact_store()
        if isinstance(store, FileArtifactStore):
            artifact = await store.get_latest_by_type(job_id, artifact_type)
            if artifact:
                return artifact
    except RuntimeError:
        pass
    return None


async def _fetch_latest_prd(job_id: str) -> Optional[dict]:
    """Fetch the latest PRD artifact with content."""
    file_artifact = await _get_artifact_from_file_store(job_id, "prd")
    if file_artifact:
        return file_artifact

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
            job_id,
        )
        if artifact_row:
            payload = dict(artifact_row)
            content = payload.get("content") or ""
            metadata = payload.get("metadata") or {}
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except Exception:
                    metadata = {}
            if isinstance(content, str) and content.startswith("[file:") and metadata.get("_file_path"):
                try:
                    with open(metadata["_file_path"], "r") as f:
                        payload["content"] = f.read()
                except Exception:
                    pass
            return payload

    return None


async def _upsert_job_truth(
    job_id: str,
    requirements: str,
    prd_content: str,
    prd_artifact_id: Optional[str],
    approved_at: Optional[datetime],
) -> None:
    requirements_hash = hash_text(requirements)
    prd_hash = hash_text(prd_content)

    pool = await postgres_client.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO job_truth (
                job_id, requirements, requirements_hash, prd_content, prd_hash, prd_artifact_id, approved_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (job_id) DO UPDATE
            SET requirements = EXCLUDED.requirements,
                requirements_hash = EXCLUDED.requirements_hash,
                prd_content = EXCLUDED.prd_content,
                prd_hash = EXCLUDED.prd_hash,
                prd_artifact_id = EXCLUDED.prd_artifact_id,
                approved_at = EXCLUDED.approved_at,
                updated_at = NOW()
            """,
            job_id,
            requirements,
            requirements_hash,
            prd_content,
            prd_hash,
            prd_artifact_id,
            approved_at,
        )


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


@router.get("/")
async def list_projects(limit: int = 50, offset: int = 0):
    """
    List all projects/jobs.

    Args:
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip

    Returns:
        List of jobs with their status
    """
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, project_id, status, workflow_stage, created_at, updated_at,
                       completed_at, metadata
                FROM jobs
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
            # Transform to match frontend expected format
            jobs = []
            for row in rows:
                job = dict(row)
                job["job_id"] = job.pop("id")
                job["stage"] = job.pop("workflow_stage")
                metadata = job.get("metadata")
                if isinstance(metadata, str):
                    try:
                        job["metadata"] = json.loads(metadata)
                    except Exception:
                        job["metadata"] = {}
                jobs.append(job)
            return {"jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            workflow_stage="initialization",
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
            message="Project workflow queued",
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
                job_id,
            )

            if not row:
                raise HTTPException(status_code=404, detail="Job not found")

            job = dict(row)
            job["job_id"] = job.pop("id")
            job["stage"] = job.pop("workflow_stage")
            metadata = job.get("metadata")
            if isinstance(metadata, str):
                try:
                    job["metadata"] = json.loads(metadata)
                except Exception:
                    job["metadata"] = {}

            task_row = await conn.fetchrow(
                """
                SELECT id, status, task_type, completed_at
                FROM tasks
                WHERE job_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                job_id,
            )
            if task_row:
                job["latest_task"] = dict(task_row)

            return job

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job and its associated data.

    Args:
        job_id: Job identifier

    Returns:
        Confirmation message
    """
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            # Check if job exists
            row = await conn.fetchrow(
                "SELECT id, status FROM jobs WHERE id = $1",
                job_id,
            )

            if not row:
                raise HTTPException(status_code=404, detail="Job not found")

            # Delete associated tasks first (foreign key constraint)
            await conn.execute(
                "DELETE FROM tasks WHERE job_id = $1",
                job_id,
            )

            # Delete associated artifacts
            await conn.execute(
                "DELETE FROM artifacts WHERE job_id = $1",
                job_id,
            )

            # Delete the job
            await conn.execute(
                "DELETE FROM jobs WHERE id = $1",
                job_id,
            )

            return {"message": f"Job {job_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/export")
async def export_job_artifacts(job_id: str):
    """Export all artifacts for a job as a downloadable ZIP file."""
    return await export_job_artifacts_handler(job_id)


@router.get("/{job_id}/prd")
async def get_job_prd(job_id: str):
    """Fetch the latest PRD for a job."""
    try:
        # Try file storage first
        file_artifact = await _get_artifact_from_file_store(job_id, "prd")
        if file_artifact:
            return file_artifact

        # Fall back to PostgreSQL
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
                job_id,
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
                job_id,
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
        # Try file storage first
        file_artifact = await _get_artifact_from_file_store(job_id, "plan")
        if file_artifact:
            return file_artifact

        # Fall back to PostgreSQL
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
                job_id,
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
                job_id,
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
        # Try file storage first
        file_artifact = await _get_artifact_from_file_store(job_id, "architecture")
        if file_artifact:
            return file_artifact

        # Fall back to PostgreSQL
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
                job_id,
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
                job_id,
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
        # Try file storage first
        file_artifact = await _get_artifact_from_file_store(job_id, "ui_ux")
        if file_artifact:
            return file_artifact

        # Fall back to PostgreSQL
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
                job_id,
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
                job_id,
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
        # Try file storage first
        file_artifact = await _get_artifact_from_file_store(job_id, "development")
        if file_artifact:
            return file_artifact

        # Fall back to PostgreSQL
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
                job_id,
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
                job_id,
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


@router.get("/{job_id}/qa")
async def get_job_qa(job_id: str):
    """Fetch the latest QA strategy and test plans for a job."""
    try:
        # Try file storage first
        file_artifact = await _get_artifact_from_file_store(job_id, "qa")
        if file_artifact:
            return file_artifact

        # Fall back to PostgreSQL
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            artifact_row = await conn.fetchrow(
                """
                SELECT id, content, metadata, updated_at, created_at
                FROM artifacts
                WHERE job_id = $1 AND type = 'qa'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
            )
            if artifact_row:
                return dict(artifact_row)

            task_row = await conn.fetchrow(
                """
                SELECT id, output_data->'qa' AS qa,
                       output_data, completed_at, created_at
                FROM tasks
                WHERE job_id = $1 AND task_type = 'qa_testing'
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
            )
            if task_row and task_row.get("qa"):
                payload = dict(task_row)
                payload["content"] = payload.pop("qa")
                return payload

        raise HTTPException(status_code=404, detail="QA strategy not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/security")
async def get_job_security(job_id: str):
    """Fetch the latest security audit for a job."""
    try:
        # Try file storage first
        file_artifact = await _get_artifact_from_file_store(job_id, "security")
        if file_artifact:
            return file_artifact

        # Fall back to PostgreSQL
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            artifact_row = await conn.fetchrow(
                """
                SELECT id, content, metadata, updated_at, created_at
                FROM artifacts
                WHERE job_id = $1 AND type = 'security'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
            )
            if artifact_row:
                return dict(artifact_row)

            task_row = await conn.fetchrow(
                """
                SELECT id, output_data->'security' AS security,
                       output_data, completed_at, created_at
                FROM tasks
                WHERE job_id = $1 AND task_type = 'security_review'
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
            )
            if task_row and task_row.get("security"):
                payload = dict(task_row)
                payload["content"] = payload.pop("security")
                return payload

        raise HTTPException(status_code=404, detail="Security audit not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/documentation")
async def get_job_documentation(job_id: str):
    """Fetch the latest documentation for a job."""
    try:
        # Try file storage first
        file_artifact = await _get_artifact_from_file_store(job_id, "documentation")
        if file_artifact:
            return file_artifact

        # Fall back to PostgreSQL
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            artifact_row = await conn.fetchrow(
                """
                SELECT id, content, metadata, updated_at, created_at
                FROM artifacts
                WHERE job_id = $1 AND type = 'documentation'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
            )
            if artifact_row:
                return dict(artifact_row)

            task_row = await conn.fetchrow(
                """
                SELECT id, output_data->'documentation' AS documentation,
                       output_data, completed_at, created_at
                FROM tasks
                WHERE job_id = $1 AND task_type = 'documentation'
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
            )
            if task_row and task_row.get("documentation"):
                payload = dict(task_row)
                payload["content"] = payload.pop("documentation")
                return payload

        raise HTTPException(status_code=404, detail="Documentation not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/support_docs")
async def get_job_support_docs(job_id: str):
    """Fetch the latest support documentation for a job."""
    try:
        # Try file storage first
        file_artifact = await _get_artifact_from_file_store(job_id, "support_docs")
        if file_artifact:
            return file_artifact

        # Fall back to PostgreSQL
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            artifact_row = await conn.fetchrow(
                """
                SELECT id, content, metadata, updated_at, created_at
                FROM artifacts
                WHERE job_id = $1 AND type = 'support_docs'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
            )
            if artifact_row:
                return dict(artifact_row)

            task_row = await conn.fetchrow(
                """
                SELECT id, output_data->'support_docs' AS support_docs,
                       output_data, completed_at, created_at
                FROM tasks
                WHERE job_id = $1 AND task_type = 'support_docs'
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
            )
            if task_row and task_row.get("support_docs"):
                payload = dict(task_row)
                payload["content"] = payload.pop("support_docs")
                return payload

        raise HTTPException(status_code=404, detail="Support documentation not found")
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
                job_id,
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


@router.get("/{job_id}/usage")
async def get_job_usage(job_id: str):
    """Return aggregated LLM usage for a job."""
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            exists = await conn.fetchval("SELECT 1 FROM jobs WHERE id = $1", job_id)
            if not exists:
                raise HTTPException(status_code=404, detail="Job not found")

            row = await conn.fetchrow(
                """
                SELECT
                    COALESCE(SUM((metadata->'llm_usage'->>'input_tokens')::bigint), 0) AS input_tokens,
                    COALESCE(SUM((metadata->'llm_usage'->>'output_tokens')::bigint), 0) AS output_tokens,
                    COALESCE(SUM((metadata->'llm_usage'->>'total_tokens')::bigint), 0) AS total_tokens,
                    COALESCE(SUM((metadata->'llm_usage'->>'calls')::bigint), 0) AS calls,
                    COALESCE(SUM((metadata->'llm_usage'->>'cost_usd')::numeric), 0) AS cost_usd,
                    SUM(
                        CASE
                            WHEN metadata->'llm_usage'->>'cost_usd' IS NOT NULL THEN 1
                            ELSE 0
                        END
                    ) AS cost_count
                FROM tasks
                WHERE job_id = $1
                """,
                job_id,
            )

        if not row:
            # This endpoint changes while jobs run; prevent intermediary/browser caching.
            return JSONResponse(
                {
                    "job_id": job_id,
                    "usage": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "calls": 0,
                        "cost_usd": None,
                        "cost_available": False,
                    },
                },
                headers={"Cache-Control": "no-store"},
            )

        cost_available = (row.get("cost_count") or 0) > 0
        cost_value = float(row.get("cost_usd") or 0) if cost_available else None

        return JSONResponse(
            {
                "job_id": job_id,
                "usage": {
                    "input_tokens": int(row.get("input_tokens") or 0),
                    "output_tokens": int(row.get("output_tokens") or 0),
                    "total_tokens": int(row.get("total_tokens") or 0),
                    "calls": int(row.get("calls") or 0),
                    "cost_usd": cost_value,
                    "cost_available": cost_available,
                },
            },
            headers={"Cache-Control": "no-store"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ApprovalRequest(BaseModel):
    """Request model for approval actions."""

    notes: Optional[str] = None


class CancelRequest(BaseModel):
    """Request model for cancel actions."""

    reason: Optional[str] = None


class ResumeRequest(BaseModel):
    """Request model for resume actions."""

    stage: str


@router.post("/{job_id}/approve")
async def approve_job(job_id: str, request: ApprovalRequest):
    """Approve a job after PRD generation.

    Note: continuation is handled by the orchestrator service (not the API process).
    """
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT status FROM jobs WHERE id = $1", job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        if row["status"] in {"canceled", "failed", "completed"}:
            raise HTTPException(
                status_code=409, detail=f"Job already ended (status={row['status']})"
            )

        # Store a naive UTC datetime for Postgres TIMESTAMP (no timezone).
        approved_at_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        approved_at = datetime.now(timezone.utc).isoformat()

        # Persist canonical truth (requirements + approved PRD)
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            job_row = await conn.fetchrow(
                "SELECT metadata FROM jobs WHERE id = $1",
                job_id,
            )
        metadata = job_row.get("metadata") if job_row else {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}
        requirements = metadata.get("requirements") if isinstance(metadata, dict) else None
        if not isinstance(requirements, str) or not requirements.strip():
            raise HTTPException(status_code=400, detail="Missing requirements for job")

        prd_artifact = await _fetch_latest_prd(job_id)
        if not prd_artifact or not prd_artifact.get("content"):
            raise HTTPException(status_code=400, detail="Missing PRD content for job")

        await _upsert_job_truth(
            job_id=job_id,
            requirements=requirements.strip(),
            prd_content=str(prd_artifact.get("content")),
            prd_artifact_id=prd_artifact.get("id"),
            approved_at=approved_at_dt,
        )

        # Mark approved only after truth is persisted, so the orchestrator doesn't race ahead.
        updated = await postgres_client.update_job_status(
            job_id=job_id, status="approved", workflow_stage="feature_tree"
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Job not found")

        await postgres_client.update_job_metadata(
            job_id=job_id,
            metadata={
                "approval_notes": request.notes,
                "approved_at": approved_at,
            },
        )

        return {"job_id": job_id, "status": "approved"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/request_changes")
async def request_changes(job_id: str, request: ApprovalRequest):
    """Request changes after PRD generation."""
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT status FROM jobs WHERE id = $1", job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        if row["status"] in {"canceled", "failed", "completed"}:
            raise HTTPException(
                status_code=409, detail=f"Job already ended (status={row['status']})"
            )

        updated = await postgres_client.update_job_status(
            job_id=job_id, status="changes_requested", workflow_stage="prd_generation"
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Job not found")
        # Clear canonical truth (PRD no longer approved)
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM job_truth WHERE job_id = $1", job_id)
        await postgres_client.update_job_metadata(
            job_id=job_id,
            metadata={
                "change_request_notes": request.notes,
                "changes_requested_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return {"job_id": job_id, "status": "changes_requested"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/restart")
async def restart_job(job_id: str):
    """Restart a failed job from initialization."""
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM jobs WHERE id = $1",
                job_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Job not found")
            if row["status"] != "failed":
                raise HTTPException(status_code=409, detail="Only failed jobs can be restarted")

            # Clear prior tasks and artifacts for a clean restart
            await conn.execute("DELETE FROM tasks WHERE job_id = $1", job_id)
            await conn.execute("DELETE FROM artifacts WHERE job_id = $1", job_id)
            await conn.execute("DELETE FROM job_truth WHERE job_id = $1", job_id)

            await conn.execute(
                """
                UPDATE jobs
                SET status = 'queued',
                    workflow_stage = 'initialization',
                    updated_at = NOW(),
                    created_at = NOW(),
                    completed_at = NULL
                WHERE id = $1
                """,
                job_id,
            )

        await postgres_client.update_job_metadata(
            job_id=job_id,
            metadata={"restarted_at": datetime.now(timezone.utc).isoformat()},
        )

        return {"job_id": job_id, "status": "queued"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, request: CancelRequest):
    """Cancel a running job and stop further processing."""
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status, workflow_stage FROM jobs WHERE id = $1",
                job_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Job not found")
            if row["status"] in {"completed", "failed", "canceled"}:
                return {"job_id": job_id, "status": row["status"], "message": "Job already ended"}

            # Mark job canceled but keep current workflow_stage for context
            await conn.execute(
                """
                UPDATE jobs
                SET status = 'canceled',
                    updated_at = NOW()
                WHERE id = $1
                """,
                job_id,
            )

            # Best-effort: mark pending/running tasks as canceled
            await conn.execute(
                """
                UPDATE tasks
                SET status = 'canceled',
                    error = 'Canceled by user'
                WHERE job_id = $1 AND status IN ('pending', 'running', 'in_progress')
                """,
                job_id,
            )

        await postgres_client.update_job_metadata(
            job_id=job_id,
            metadata={
                "canceled_at": datetime.now(timezone.utc).isoformat(),
                "cancel_reason": request.reason,
            },
        )

        try:
            await publish_job_aborted(job_id, request.reason or "Canceled by user")
        except Exception:
            pass

        return {"job_id": job_id, "status": "canceled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/resume")
async def resume_job(job_id: str, request: ResumeRequest):
    """Resume a job from a specific stage (re-runs downstream stages)."""
    try:
        # Validate stage
        valid_stages = {
            WorkflowStage.FEATURE_TREE.value,
            WorkflowStage.PLAN_GENERATION.value,
            WorkflowStage.ARCHITECTURE_DESIGN.value,
            WorkflowStage.UIUX_DESIGN.value,
            WorkflowStage.DEVELOPMENT.value,
            WorkflowStage.QA_TESTING.value,
            WorkflowStage.SECURITY_REVIEW.value,
            WorkflowStage.DOCUMENTATION.value,
            WorkflowStage.SUPPORT_DOCS.value,
            WorkflowStage.PM_REVIEW.value,
            WorkflowStage.DELIVERY.value,
        }
        if request.stage not in valid_stages:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage '{request.stage}'. Valid: {', '.join(sorted(valid_stages))}",
            )

        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM jobs WHERE id = $1",
                job_id,
            )
            if not row:
                raise HTTPException(status_code=404, detail="Job not found")

            # Mark any pending/running tasks as canceled to avoid overlaps
            await conn.execute(
                """
                UPDATE tasks
                SET status = 'canceled',
                    error = 'Canceled for resume'
                WHERE job_id = $1 AND status IN ('pending', 'running', 'in_progress')
                """,
                job_id,
            )

            # Set job to approved so orchestrator picks it up
            await conn.execute(
                """
                UPDATE jobs
                SET status = 'approved',
                    workflow_stage = $2,
                    updated_at = NOW()
                WHERE id = $1
                """,
                job_id,
                request.stage,
            )

        await postgres_client.update_job_metadata(
            job_id=job_id,
            metadata={
                "resume_from_stage": request.stage,
                "resume_requested_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "job_id": job_id,
            "status": "approved",
            "resume_from_stage": request.stage,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
