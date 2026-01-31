"""API routes for project management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...orchestration.master_agent import MasterAgent
from ...infrastructure.redis_client import redis_client
from ...infrastructure.postgres_client import postgres_client
from ...skills.manager import SkillsManager
from ...config import settings


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
        # Initialize components
        skills_manager = SkillsManager(settings.skills_directory)

        # Create master agent
        master_agent = MasterAgent(
            redis_client=redis_client,
            postgres_client=postgres_client,
            skills_manager=skills_manager
        )

        # Start orchestration (async - will complete in background)
        # TODO: Make this truly async with background tasks
        result = await master_agent.orchestrate_project(
            project_id=request.project_id,
            requirements=request.requirements
        )

        return ProjectResponse(
            job_id=result["job_id"],
            project_id=request.project_id,
            status=result["status"],
            message=f"Project workflow {'completed' if result['status'] == 'completed' else 'failed'}"
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
                SELECT id, project_id, status, workflow_stage, created_at, updated_at
                FROM jobs
                WHERE id = $1
                """,
                job_id
            )

            if not row:
                raise HTTPException(status_code=404, detail="Job not found")

            return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
