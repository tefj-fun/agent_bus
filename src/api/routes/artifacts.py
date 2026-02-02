"""API routes for artifact management and export."""

import os
import tempfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

from ...config import settings
from ...storage.artifact_store import get_artifact_store, FileArtifactStore


router = APIRouter()


class ArtifactInfo(BaseModel):
    """Artifact information model."""

    id: str
    job_id: str
    type: str
    agent_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class JobArtifactsResponse(BaseModel):
    """Response model for job artifacts listing."""

    job_id: str
    artifacts: List[ArtifactInfo]
    storage_backend: str


class ExportResponse(BaseModel):
    """Response model for export operations."""

    job_id: str
    export_path: str
    message: str


@router.get("/jobs", response_model=List[str])
async def list_jobs_with_artifacts():
    """List all job IDs that have artifacts stored.

    Only available when using file-based storage backend.
    """
    if settings.artifact_storage_backend != "file":
        raise HTTPException(
            status_code=400,
            detail="Job listing only available with file storage backend",
        )

    try:
        store = get_artifact_store()
        if isinstance(store, FileArtifactStore):
            return store.list_jobs()
        return []
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}", response_model=JobArtifactsResponse)
async def get_job_artifacts(job_id: str):
    """Get all artifacts for a job.

    Returns metadata about all artifacts without the full content.
    """
    if settings.artifact_storage_backend != "file":
        raise HTTPException(
            status_code=400,
            detail="This endpoint only available with file storage backend",
        )

    try:
        store = get_artifact_store()
        artifacts = await store.get_by_job(job_id)

        if not artifacts:
            raise HTTPException(status_code=404, detail=f"No artifacts found for job {job_id}")

        return JobArtifactsResponse(
            job_id=job_id,
            artifacts=[
                ArtifactInfo(
                    id=a.get("id", ""),
                    job_id=job_id,
                    type=a.get("type", ""),
                    agent_id=a.get("agent_id"),
                    created_at=a.get("created_at"),
                    updated_at=a.get("updated_at"),
                )
                for a in artifacts
            ],
            storage_backend=settings.artifact_storage_backend,
        )
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}/{artifact_type}")
async def get_artifact_content(job_id: str, artifact_type: str):
    """Get specific artifact content for a job.

    Args:
        job_id: Job identifier
        artifact_type: Type of artifact (prd, architecture, etc.)

    Returns:
        Artifact content and metadata
    """
    if settings.artifact_storage_backend != "file":
        raise HTTPException(
            status_code=400,
            detail="This endpoint only available with file storage backend",
        )

    try:
        store = get_artifact_store()
        if isinstance(store, FileArtifactStore):
            artifact = await store.get_latest_by_type(job_id, artifact_type)
            if artifact:
                return artifact

        raise HTTPException(
            status_code=404, detail=f"Artifact '{artifact_type}' not found for job {job_id}"
        )
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}/export")
async def export_job_artifacts(job_id: str):
    """Export all artifacts for a job as a downloadable ZIP file.

    This bundles all generated outputs (PRD, architecture, plans, etc.)
    into a single portable archive.

    Args:
        job_id: Job identifier

    Returns:
        ZIP file download
    """
    if settings.artifact_storage_backend != "file":
        raise HTTPException(
            status_code=400,
            detail="Export only available with file storage backend",
        )

    try:
        store = get_artifact_store()
        if not isinstance(store, FileArtifactStore):
            raise HTTPException(status_code=500, detail="Invalid store type")

        # Create temp directory for the zip file
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, f"{job_id}.zip")
            await store.create_bundle(job_id, zip_path)

            if not os.path.exists(zip_path):
                raise HTTPException(status_code=500, detail="Failed to create export bundle")

            return FileResponse(
                path=zip_path,
                filename=f"{job_id}_artifacts.zip",
                media_type="application/zip",
            )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No artifacts found for job {job_id}")
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}/export/path", response_model=ExportResponse)
async def export_job_to_path(job_id: str, output_dir: Optional[str] = None):
    """Export job artifacts to a directory on the server.

    Args:
        job_id: Job identifier
        output_dir: Target directory (defaults to exports/ in artifact output dir)

    Returns:
        Path to the exported directory
    """
    if settings.artifact_storage_backend != "file":
        raise HTTPException(
            status_code=400,
            detail="Export only available with file storage backend",
        )

    try:
        store = get_artifact_store()
        if not isinstance(store, FileArtifactStore):
            raise HTTPException(status_code=500, detail="Invalid store type")

        # Default export location
        if not output_dir:
            output_dir = os.path.join(settings.artifact_output_dir, "exports")

        export_path = await store.export_job(job_id, output_dir)

        return ExportResponse(
            job_id=job_id,
            export_path=export_path,
            message=f"Artifacts exported successfully to {export_path}",
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No artifacts found for job {job_id}")
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storage/info")
async def get_storage_info():
    """Get information about the artifact storage configuration."""
    info = {
        "backend": settings.artifact_storage_backend,
        "output_dir": settings.artifact_output_dir if settings.artifact_storage_backend == "file" else None,
    }

    if settings.artifact_storage_backend == "file":
        try:
            store = get_artifact_store()
            if isinstance(store, FileArtifactStore):
                jobs = store.list_jobs()
                info["total_jobs"] = len(jobs)
                info["output_dir_exists"] = os.path.exists(settings.artifact_output_dir)
        except RuntimeError:
            info["initialized"] = False

    return info
