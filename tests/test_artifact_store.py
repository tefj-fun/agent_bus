"""Tests for the artifact storage module."""

import json
import os
import pytest
import tempfile
import shutil
from pathlib import Path

from src.storage.artifact_store import (
    FileArtifactStore,
    ArtifactMetadata,
    init_artifact_store,
    get_artifact_store,
)


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for artifact storage."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def artifact_store(temp_output_dir):
    """Create a FileArtifactStore instance."""
    return FileArtifactStore(temp_output_dir)


class TestFileArtifactStore:
    """Tests for FileArtifactStore."""

    @pytest.mark.asyncio
    async def test_save_artifact(self, artifact_store, temp_output_dir):
        """Test saving an artifact creates proper file structure."""
        artifact_id = "prd_agent_prd_job123"
        agent_id = "prd_agent"
        job_id = "job123"
        artifact_type = "prd"
        content = "# Product Requirements\n\nThis is the PRD content."
        metadata = {"version": "1.0"}

        result = await artifact_store.save(
            artifact_id=artifact_id,
            agent_id=agent_id,
            job_id=job_id,
            artifact_type=artifact_type,
            content=content,
            metadata=metadata,
        )

        # Check return value
        assert isinstance(result, ArtifactMetadata)
        assert result.id == artifact_id
        assert result.agent_id == agent_id
        assert result.job_id == job_id
        assert result.artifact_type == artifact_type
        assert result.metadata == metadata

        # Check files were created
        job_dir = Path(temp_output_dir) / job_id
        assert job_dir.exists()
        assert (job_dir / "prd.md").exists()
        assert (job_dir / "prd.meta.json").exists()
        assert (job_dir / "manifest.json").exists()

        # Check content file
        with open(job_dir / "prd.md", "r") as f:
            assert f.read() == content

        # Check metadata file
        with open(job_dir / "prd.meta.json", "r") as f:
            meta = json.load(f)
            assert meta["id"] == artifact_id
            assert meta["metadata"]["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_get_artifact(self, artifact_store):
        """Test retrieving an artifact by ID."""
        artifact_id = "prd_agent_prd_job456"
        content = "Test PRD content"

        # Save first
        await artifact_store.save(
            artifact_id=artifact_id,
            agent_id="prd_agent",
            job_id="job456",
            artifact_type="prd",
            content=content,
            metadata={"test": True},
        )

        # Retrieve
        artifact = await artifact_store.get(artifact_id)

        assert artifact is not None
        assert artifact["id"] == artifact_id
        assert artifact["content"] == content
        assert artifact["metadata"]["test"] is True
        assert artifact["type"] == "prd"
        assert artifact["job_id"] == "job456"

    @pytest.mark.asyncio
    async def test_get_nonexistent_artifact(self, artifact_store):
        """Test retrieving a non-existent artifact returns None."""
        result = await artifact_store.get("nonexistent_artifact_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_job(self, artifact_store):
        """Test retrieving all artifacts for a job."""
        job_id = "job789"

        # Save multiple artifacts
        await artifact_store.save(
            artifact_id=f"prd_agent_prd_{job_id}",
            agent_id="prd_agent",
            job_id=job_id,
            artifact_type="prd",
            content="PRD content",
        )
        await artifact_store.save(
            artifact_id=f"architect_agent_architecture_{job_id}",
            agent_id="architect_agent",
            job_id=job_id,
            artifact_type="architecture",
            content="Architecture content",
        )

        # Get all artifacts for job
        artifacts = await artifact_store.get_by_job(job_id)

        assert len(artifacts) == 2
        types = [a["type"] for a in artifacts]
        assert "prd" in types
        assert "architecture" in types

    @pytest.mark.asyncio
    async def test_get_by_job_with_type_filter(self, artifact_store):
        """Test retrieving artifacts filtered by type."""
        job_id = "job_filter"

        await artifact_store.save(
            artifact_id=f"agent_prd_{job_id}",
            agent_id="agent",
            job_id=job_id,
            artifact_type="prd",
            content="PRD",
        )
        await artifact_store.save(
            artifact_id=f"agent_architecture_{job_id}",
            agent_id="agent",
            job_id=job_id,
            artifact_type="architecture",
            content="Arch",
        )

        # Filter by type
        artifacts = await artifact_store.get_by_job(job_id, artifact_type="prd")

        assert len(artifacts) == 1
        assert artifacts[0]["type"] == "prd"

    @pytest.mark.asyncio
    async def test_get_latest_by_type(self, artifact_store):
        """Test getting the latest artifact of a specific type."""
        job_id = "job_latest"

        await artifact_store.save(
            artifact_id=f"agent_prd_{job_id}",
            agent_id="agent",
            job_id=job_id,
            artifact_type="prd",
            content="Latest PRD content",
        )

        artifact = await artifact_store.get_latest_by_type(job_id, "prd")

        assert artifact is not None
        assert artifact["content"] == "Latest PRD content"

    @pytest.mark.asyncio
    async def test_delete_artifact(self, artifact_store, temp_output_dir):
        """Test deleting an artifact."""
        job_id = "job_delete"
        artifact_id = f"agent_prd_{job_id}"

        await artifact_store.save(
            artifact_id=artifact_id,
            agent_id="agent",
            job_id=job_id,
            artifact_type="prd",
            content="To be deleted",
        )

        # Verify it exists
        job_dir = Path(temp_output_dir) / job_id
        assert (job_dir / "prd.md").exists()

        # Delete
        result = await artifact_store.delete(artifact_id)
        assert result is True

        # Verify deleted
        assert not (job_dir / "prd.md").exists()
        assert not (job_dir / "prd.meta.json").exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_artifact(self, artifact_store):
        """Test deleting a non-existent artifact returns False."""
        result = await artifact_store.delete("nonexistent_id")
        assert result is False

    @pytest.mark.asyncio
    async def test_export_job(self, artifact_store, temp_output_dir):
        """Test exporting all artifacts for a job."""
        job_id = "job_export"

        # Create artifacts
        await artifact_store.save(
            artifact_id=f"agent_prd_{job_id}",
            agent_id="agent",
            job_id=job_id,
            artifact_type="prd",
            content="PRD for export",
        )
        await artifact_store.save(
            artifact_id=f"agent_architecture_{job_id}",
            agent_id="agent",
            job_id=job_id,
            artifact_type="architecture",
            content="Architecture for export",
        )

        # Export to different directory
        export_dir = tempfile.mkdtemp()
        try:
            export_path = await artifact_store.export_job(job_id, export_dir)

            # Check export
            assert os.path.exists(export_path)
            assert (Path(export_path) / "prd.md").exists()
            assert (Path(export_path) / "architecture.md").exists()
            assert (Path(export_path) / "manifest.json").exists()
        finally:
            shutil.rmtree(export_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_create_bundle(self, artifact_store, temp_output_dir):
        """Test creating a ZIP bundle of artifacts."""
        job_id = "job_bundle"

        await artifact_store.save(
            artifact_id=f"agent_prd_{job_id}",
            agent_id="agent",
            job_id=job_id,
            artifact_type="prd",
            content="PRD for bundle",
        )

        # Create bundle
        bundle_dir = tempfile.mkdtemp()
        try:
            bundle_path = os.path.join(bundle_dir, f"{job_id}.zip")
            result_path = await artifact_store.create_bundle(job_id, bundle_path)

            assert os.path.exists(result_path)
            assert result_path.endswith(".zip")
        finally:
            shutil.rmtree(bundle_dir, ignore_errors=True)

    def test_list_jobs(self, artifact_store, temp_output_dir):
        """Test listing all jobs with artifacts."""
        # Initially empty
        assert artifact_store.list_jobs() == []

        # Create jobs manually (simulating artifacts)
        for job_id in ["job_a", "job_b", "job_c"]:
            job_dir = Path(temp_output_dir) / job_id
            job_dir.mkdir(parents=True)
            with open(job_dir / "manifest.json", "w") as f:
                json.dump({"job_id": job_id, "artifacts": {}}, f)

        jobs = artifact_store.list_jobs()
        assert len(jobs) == 3
        assert set(jobs) == {"job_a", "job_b", "job_c"}

    @pytest.mark.asyncio
    async def test_update_existing_artifact(self, artifact_store):
        """Test that saving an artifact with same type updates the existing one."""
        job_id = "job_update"
        artifact_id = f"agent_prd_{job_id}"

        # Save initial
        await artifact_store.save(
            artifact_id=artifact_id,
            agent_id="agent",
            job_id=job_id,
            artifact_type="prd",
            content="Original content",
        )

        # Update
        await artifact_store.save(
            artifact_id=artifact_id,
            agent_id="agent",
            job_id=job_id,
            artifact_type="prd",
            content="Updated content",
        )

        # Verify update
        artifact = await artifact_store.get(artifact_id)
        assert artifact["content"] == "Updated content"

    def test_type_extensions(self, artifact_store):
        """Test that artifact types map to correct file extensions."""
        assert artifact_store._get_extension("prd") == ".md"
        assert artifact_store._get_extension("architecture") == ".md"
        assert artifact_store._get_extension("code") == ".txt"
        assert artifact_store._get_extension("unknown") == ".txt"


class TestArtifactStoreInitialization:
    """Tests for artifact store initialization."""

    def test_init_artifact_store(self, temp_output_dir):
        """Test initializing the global artifact store."""
        store = init_artifact_store(temp_output_dir)

        assert isinstance(store, FileArtifactStore)
        assert store.output_dir == Path(temp_output_dir)

    def test_get_artifact_store_uninitialized(self):
        """Test that getting store before init raises error."""
        # Reset global store
        import src.storage.artifact_store as store_module
        store_module.artifact_store = None

        with pytest.raises(RuntimeError):
            get_artifact_store()

    def test_output_directory_created(self, temp_output_dir):
        """Test that output directory is created if it doesn't exist."""
        new_dir = os.path.join(temp_output_dir, "new_output_dir")
        store = FileArtifactStore(new_dir)

        assert os.path.exists(new_dir)
