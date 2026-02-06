"""Orchestrator service.

Moves long-running orchestration out of the FastAPI process.

Behavior:
- Polls Postgres for queued jobs
- Claims one job atomically
- Runs MasterAgent.orchestrate_project() for that job

This ensures jobs continue even if the API process restarts.
"""

import asyncio

from .master_agent import MasterAgent
from ..infrastructure.redis_client import redis_client
from ..infrastructure.postgres_client import postgres_client
from ..skills.manager import SkillsManager
from ..storage.artifact_store import init_artifact_store
from ..config import settings


class OrchestratorService:
    def __init__(self, poll_secs: float = 1.0):
        self.poll_secs = poll_secs
        self.skills_manager = SkillsManager(settings.skills_directory)
        self.master = MasterAgent(
            redis_client=redis_client,
            postgres_client=postgres_client,
            skills_manager=self.skills_manager,
        )

    async def run_forever(self):
        print("[Orchestrator] Starting...")
        await redis_client.connect()
        await postgres_client.connect()
        print(f"[Orchestrator] Connected to Redis at {settings.redis_host}:{settings.redis_port}")
        print(
            f"[Orchestrator] Connected to PostgreSQL at {settings.postgres_host}:{settings.postgres_port}"
        )

        # Initialize artifact store for file-based output storage
        if settings.artifact_storage_backend == "file":
            init_artifact_store(settings.artifact_output_dir)
            print(f"[Orchestrator] Artifact store initialized at {settings.artifact_output_dir}")

        while True:
            try:
                # Prefer newly queued jobs; if none, pick up approved jobs (plan stage)
                job = await postgres_client.claim_next_job(
                    from_status="queued", to_status="orchestrating"
                )
                job_kind = "queued"
                if not job:
                    job = await postgres_client.claim_next_job(
                        from_status="approved", to_status="orchestrating_plan"
                    )
                    job_kind = "approved"
                if not job:
                    job = await postgres_client.claim_next_job(
                        from_status="changes_requested", to_status="orchestrating_prd_revision"
                    )
                    job_kind = "changes_requested"

                if not job:
                    await asyncio.sleep(self.poll_secs)
                    continue

                job_id = job["id"]
                project_id = job["project_id"]
                metadata = job.get("metadata") or {}

                # metadata may arrive as dict (asyncpg jsonb) or string
                if isinstance(metadata, str):
                    try:
                        import json

                        metadata = json.loads(metadata)
                    except Exception:
                        metadata = {}

                if job_kind == "approved":
                    print(f"[Orchestrator] Claimed APPROVED job {job_id} project={project_id}")
                    await self.master.continue_after_approval(job_id)
                    continue
                if job_kind == "changes_requested":
                    print(f"[Orchestrator] Claimed CHANGES_REQUESTED job {job_id} project={project_id}")
                    await self.master.continue_after_change_request(job_id)
                    continue

                # queued job: run PRD stage
                requirements = metadata.get("requirements") if isinstance(metadata, dict) else None
                if not requirements:
                    print(f"[Orchestrator] Job {job_id} missing requirements; failing")
                    await postgres_client.update_job_status(
                        job_id, status="failed", workflow_stage="failed"
                    )
                    continue

                print(f"[Orchestrator] Claimed job {job_id} project={project_id}")

                await self.master.orchestrate_project(
                    project_id=project_id,
                    requirements=requirements,
                    job_id=job_id,
                    create_job=False,
                )

            except Exception as e:
                print(f"[Orchestrator] Error: {type(e).__name__}: {e}")
                await asyncio.sleep(self.poll_secs)


async def main():
    poll = float(getattr(settings, "orchestrator_poll_secs", 1.0))
    svc = OrchestratorService(poll_secs=poll)
    await svc.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
