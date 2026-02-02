"""Artifact storage abstraction for decoupled output storage.

This module provides a pluggable storage backend for artifacts, separating
generated outputs from the system database for easier portability.
"""

import json
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ArtifactMetadata:
    """Metadata for a stored artifact."""

    id: str
    agent_id: str
    job_id: str
    artifact_type: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_path: Optional[str] = None  # Relative path for file-based storage


class ArtifactStore(ABC):
    """Abstract base class for artifact storage backends."""

    @abstractmethod
    async def save(
        self,
        artifact_id: str,
        agent_id: str,
        job_id: str,
        artifact_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ArtifactMetadata:
        """Save an artifact to storage.

        Args:
            artifact_id: Unique identifier for the artifact
            agent_id: ID of the agent that created the artifact
            job_id: ID of the job this artifact belongs to
            artifact_type: Type of artifact (prd, architecture, etc.)
            content: Artifact content
            metadata: Additional metadata

        Returns:
            ArtifactMetadata with storage information
        """
        pass

    @abstractmethod
    async def get(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an artifact by ID.

        Args:
            artifact_id: Unique identifier for the artifact

        Returns:
            Dict with artifact data including content, or None if not found
        """
        pass

    @abstractmethod
    async def get_by_job(
        self, job_id: str, artifact_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve all artifacts for a job.

        Args:
            job_id: Job identifier
            artifact_type: Optional filter by artifact type

        Returns:
            List of artifact data dicts
        """
        pass

    @abstractmethod
    async def delete(self, artifact_id: str) -> bool:
        """Delete an artifact.

        Args:
            artifact_id: Unique identifier for the artifact

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def export_job(self, job_id: str, output_path: str) -> str:
        """Export all artifacts for a job to a directory.

        Args:
            job_id: Job identifier
            output_path: Directory to export to

        Returns:
            Path to the exported directory
        """
        pass


class FileArtifactStore(ArtifactStore):
    """File-based artifact storage.

    Stores artifacts as files organized by job_id:
        {output_dir}/
            {job_id}/
                manifest.json          # Index of all artifacts
                prd.md                 # PRD content
                prd.meta.json          # PRD metadata
                architecture.md        # Architecture content
                ...

    This makes outputs:
    - Portable: Just copy the job directory
    - Human-readable: Content stored as markdown files
    - Self-contained: Each job directory has everything needed
    """

    # Map artifact types to file extensions
    TYPE_EXTENSIONS = {
        "prd": ".md",
        "plan": ".md",
        "architecture": ".md",
        "ui_ux": ".md",
        "development": ".md",
        "qa": ".md",
        "security": ".md",
        "documentation": ".md",
        "support_docs": ".md",
        "delivery": ".md",
        "code": ".txt",  # Could be multiple files
    }

    def __init__(self, output_dir: str):
        """Initialize file artifact store.

        Args:
            output_dir: Base directory for storing artifacts
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_job_dir(self, job_id: str) -> Path:
        """Get the directory for a job's artifacts."""
        job_dir = self.output_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def _get_extension(self, artifact_type: str) -> str:
        """Get file extension for artifact type."""
        return self.TYPE_EXTENSIONS.get(artifact_type, ".txt")

    def _get_artifact_filename(self, artifact_type: str) -> str:
        """Get filename for artifact content."""
        ext = self._get_extension(artifact_type)
        return f"{artifact_type}{ext}"

    def _get_metadata_filename(self, artifact_type: str) -> str:
        """Get filename for artifact metadata."""
        return f"{artifact_type}.meta.json"

    def _load_manifest(self, job_dir: Path) -> Dict[str, Any]:
        """Load or create the job manifest."""
        manifest_path = job_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r") as f:
                return json.load(f)
        return {
            "job_id": job_dir.name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "artifacts": {},
        }

    def _save_manifest(self, job_dir: Path, manifest: Dict[str, Any]) -> None:
        """Save the job manifest."""
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        manifest_path = job_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

    async def save(
        self,
        artifact_id: str,
        agent_id: str,
        job_id: str,
        artifact_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ArtifactMetadata:
        """Save an artifact to the file system."""
        job_dir = self._get_job_dir(job_id)
        now = datetime.now(timezone.utc).isoformat()

        # Write content file
        content_filename = self._get_artifact_filename(artifact_type)
        content_path = job_dir / content_filename
        with open(content_path, "w") as f:
            f.write(content)

        # Create metadata
        artifact_meta = ArtifactMetadata(
            id=artifact_id,
            agent_id=agent_id,
            job_id=job_id,
            artifact_type=artifact_type,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
            file_path=content_filename,
        )

        # Write metadata file
        meta_filename = self._get_metadata_filename(artifact_type)
        meta_path = job_dir / meta_filename
        with open(meta_path, "w") as f:
            json.dump(
                {
                    "id": artifact_meta.id,
                    "agent_id": artifact_meta.agent_id,
                    "job_id": artifact_meta.job_id,
                    "artifact_type": artifact_meta.artifact_type,
                    "created_at": artifact_meta.created_at,
                    "updated_at": artifact_meta.updated_at,
                    "metadata": artifact_meta.metadata,
                    "file_path": artifact_meta.file_path,
                },
                f,
                indent=2,
            )

        # Update manifest
        manifest = self._load_manifest(job_dir)
        manifest["artifacts"][artifact_type] = {
            "id": artifact_id,
            "agent_id": agent_id,
            "file": content_filename,
            "metadata_file": meta_filename,
            "updated_at": now,
        }
        self._save_manifest(job_dir, manifest)

        return artifact_meta

    async def get(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an artifact by ID."""
        # artifact_id format: {agent_id}_{artifact_type}_{job_id}
        parts = artifact_id.split("_")
        if len(parts) < 3:
            return None

        # Extract job_id (last part) and artifact_type (second to last)
        job_id = parts[-1]
        artifact_type = parts[-2]

        job_dir = self.output_dir / job_id
        if not job_dir.exists():
            return None

        content_path = job_dir / self._get_artifact_filename(artifact_type)
        meta_path = job_dir / self._get_metadata_filename(artifact_type)

        if not content_path.exists():
            return None

        # Read content
        with open(content_path, "r") as f:
            content = f.read()

        # Read metadata if exists
        metadata = {}
        if meta_path.exists():
            with open(meta_path, "r") as f:
                metadata = json.load(f)

        return {
            "id": artifact_id,
            "content": content,
            "metadata": metadata.get("metadata", {}),
            "created_at": metadata.get("created_at"),
            "updated_at": metadata.get("updated_at"),
            "agent_id": metadata.get("agent_id"),
            "job_id": job_id,
            "type": artifact_type,
        }

    async def get_by_job(
        self, job_id: str, artifact_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve all artifacts for a job."""
        job_dir = self.output_dir / job_id
        if not job_dir.exists():
            return []

        manifest = self._load_manifest(job_dir)
        artifacts = []

        for atype, info in manifest.get("artifacts", {}).items():
            if artifact_type and atype != artifact_type:
                continue

            content_path = job_dir / info["file"]
            if not content_path.exists():
                continue

            with open(content_path, "r") as f:
                content = f.read()

            # Load metadata
            meta_path = job_dir / info.get("metadata_file", f"{atype}.meta.json")
            metadata = {}
            if meta_path.exists():
                with open(meta_path, "r") as f:
                    metadata = json.load(f)

            artifacts.append(
                {
                    "id": info["id"],
                    "content": content,
                    "metadata": metadata.get("metadata", {}),
                    "created_at": metadata.get("created_at"),
                    "updated_at": info.get("updated_at"),
                    "agent_id": info.get("agent_id"),
                    "job_id": job_id,
                    "type": atype,
                }
            )

        return artifacts

    async def get_latest_by_type(
        self, job_id: str, artifact_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get the latest artifact of a specific type for a job."""
        artifacts = await self.get_by_job(job_id, artifact_type)
        if not artifacts:
            return None
        # Return most recently updated
        return max(artifacts, key=lambda a: a.get("updated_at", ""))

    async def delete(self, artifact_id: str) -> bool:
        """Delete an artifact."""
        parts = artifact_id.split("_")
        if len(parts) < 3:
            return False

        job_id = parts[-1]
        artifact_type = parts[-2]

        job_dir = self.output_dir / job_id
        if not job_dir.exists():
            return False

        content_path = job_dir / self._get_artifact_filename(artifact_type)
        meta_path = job_dir / self._get_metadata_filename(artifact_type)

        deleted = False
        if content_path.exists():
            content_path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()

        # Update manifest
        if deleted:
            manifest = self._load_manifest(job_dir)
            manifest["artifacts"].pop(artifact_type, None)
            self._save_manifest(job_dir, manifest)

        return deleted

    async def export_job(self, job_id: str, output_path: str) -> str:
        """Export all artifacts for a job to a directory."""
        job_dir = self.output_dir / job_id
        if not job_dir.exists():
            raise FileNotFoundError(f"No artifacts found for job {job_id}")

        export_dir = Path(output_path)
        export_dir.mkdir(parents=True, exist_ok=True)

        # Copy entire job directory
        export_job_dir = export_dir / job_id
        if export_job_dir.exists():
            shutil.rmtree(export_job_dir)
        shutil.copytree(job_dir, export_job_dir)

        return str(export_job_dir)

    async def create_bundle(self, job_id: str, output_path: str) -> str:
        """Create a zip bundle of all artifacts for a job.

        Args:
            job_id: Job identifier
            output_path: Path for the output zip file

        Returns:
            Path to the created zip file
        """
        job_dir = self.output_dir / job_id
        if not job_dir.exists():
            raise FileNotFoundError(f"No artifacts found for job {job_id}")

        # Create zip archive
        output_path = Path(output_path)
        if not output_path.suffix:
            output_path = output_path.with_suffix(".zip")

        shutil.make_archive(
            str(output_path.with_suffix("")),  # Base name without extension
            "zip",
            job_dir.parent,
            job_dir.name,
        )

        return str(output_path)

    def list_jobs(self) -> List[str]:
        """List all job IDs that have artifacts stored."""
        if not self.output_dir.exists():
            return []
        return [
            d.name
            for d in self.output_dir.iterdir()
            if d.is_dir() and (d / "manifest.json").exists()
        ]


# Global artifact store instance (initialized in main.py)
artifact_store: Optional[ArtifactStore] = None


def get_artifact_store() -> ArtifactStore:
    """Get the global artifact store instance."""
    if artifact_store is None:
        raise RuntimeError("Artifact store not initialized")
    return artifact_store


def init_artifact_store(output_dir: str) -> FileArtifactStore:
    """Initialize the global artifact store.

    Args:
        output_dir: Directory for storing artifacts

    Returns:
        Initialized FileArtifactStore instance
    """
    global artifact_store
    artifact_store = FileArtifactStore(output_dir)
    return artifact_store
