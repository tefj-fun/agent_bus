"""Master Agent for orchestrating the SWE engineering workflow."""

import asyncio
import json
import uuid
from typing import Dict, Optional
from datetime import datetime

from .workflow import WorkflowStateMachine, WorkflowStage
from ..infrastructure.redis_client import RedisClient
from ..infrastructure.postgres_client import PostgresClient
from ..infrastructure.anthropic_client import anthropic_client
from ..skills.manager import SkillsManager
from ..api.routes.events import publish_stage_started, publish_stage_completed, publish_job_failed, publish_job_started
from ..config import settings
from ..utils.truth import alignment_check, hash_text
from ..storage.artifact_store import get_artifact_store, FileArtifactStore

STAGE_ARTIFACT_TYPES = {
    WorkflowStage.FEATURE_TREE: "feature_tree",
    WorkflowStage.PLAN_GENERATION: "plan",
    WorkflowStage.ARCHITECTURE_DESIGN: "architecture",
    WorkflowStage.UIUX_DESIGN: "ui_ux",
    WorkflowStage.DEVELOPMENT: "development",
    WorkflowStage.QA_TESTING: "qa",
    WorkflowStage.SECURITY_REVIEW: "security",
    WorkflowStage.DOCUMENTATION: "documentation",
    WorkflowStage.SUPPORT_DOCS: "support_docs",
    WorkflowStage.PM_REVIEW: "pm_review",
    # Delivery is a packaging summary; skip alignment guardrails to avoid false negatives.
}


class MasterAgent:
    """
    Master orchestration agent (SWE Engineering Manager).

    Coordinates all specialized agents through the workflow pipeline.
    """

    def __init__(
        self,
        redis_client: RedisClient,
        postgres_client: PostgresClient,
        skills_manager: SkillsManager,
    ):
        self.redis = redis_client
        self.postgres = postgres_client
        self.anthropic = anthropic_client
        self.skills_manager = skills_manager
        self.workflow = WorkflowStateMachine()
        self._truth_cache: Optional[Dict[str, str]] = None

    async def orchestrate_project(
        self,
        project_id: str,
        requirements: str,
        job_id: Optional[str] = None,
        create_job: bool = True,
    ) -> Dict:
        """
        Main orchestration loop for a project.

        Args:
            project_id: Unique project identifier
            requirements: Sales requirements input

        Returns:
            Final project results
        """
        # Create job
        if job_id is None:
            job_id = f"job_{uuid.uuid4().hex[:12]}"
        if create_job:
            await self.postgres.create_job(
                job_id=job_id,
                project_id=project_id,
                status="queued",
                workflow_stage=WorkflowStage.INITIALIZATION.value,
            )

        print(f"[MasterAgent] Starting job {job_id} for project {project_id}")

        try:
            # Phase 1 scope: PRD only. Later phases can enable downstream stages.
            prd_result = await self._execute_stage(
                job_id=job_id,
                project_id=project_id,
                stage=WorkflowStage.PRD_GENERATION,
                inputs={"requirements": requirements},
            )

            await self.postgres.update_job_status(
                job_id=job_id,
                status="waiting_for_approval",
                workflow_stage=WorkflowStage.WAITING_FOR_APPROVAL.value,
            )

            print(f"[MasterAgent] Job {job_id} ready for approval after PRD generation")

            return {
                "job_id": job_id,
                "status": "waiting_for_approval",
                "results": {"prd": prd_result},
            }

        except JobCanceledError as e:
            print(f"[MasterAgent] Job {job_id} canceled: {str(e)}")
            await self.postgres.update_job_status(job_id=job_id, status="canceled")
            return {"job_id": job_id, "status": "canceled", "error": str(e)}
        except Exception as e:
            print(f"[MasterAgent] Job {job_id} failed: {str(e)}")

            # Publish job failed event
            try:
                await publish_job_failed(job_id, str(e))
            except Exception as pub_err:
                print(f"[MasterAgent] Failed to publish job_failed event: {pub_err}")

            try:
                # Capture last known stage before we overwrite it with FAILED
                pool = await self.postgres.get_pool()
                async with pool.acquire() as conn:
                    stage_row = await conn.fetchrow(
                        "SELECT workflow_stage FROM jobs WHERE id = $1",
                        job_id,
                    )
                failed_stage = stage_row["workflow_stage"] if stage_row else None
                metadata_update = {"error": str(e)}
                if failed_stage and failed_stage != WorkflowStage.FAILED.value:
                    metadata_update["failed_stage"] = failed_stage

                await self.postgres.update_job_metadata(
                    job_id=job_id,
                    metadata=metadata_update,
                )
            except Exception as meta_err:
                print(f"[MasterAgent] Failed to persist job error metadata: {meta_err}")

            await self.postgres.update_job_status(
                job_id=job_id, status="failed", workflow_stage=WorkflowStage.FAILED.value
            )

            return {"job_id": job_id, "status": "failed", "error": str(e)}

    async def continue_after_approval(self, job_id: str) -> Dict:
        """
        Continue the workflow after HITL approval.

        Args:
            job_id: Job identifier

        Returns:
            Updated job results
        """
        try:
            project_id, requirements, metadata = await self._fetch_job_context(job_id)
            if not project_id:
                raise ValueError(f"Job {job_id} not found")

            truth = await self._fetch_job_truth(job_id)
            if not truth:
                truth = await self._backfill_job_truth(job_id, requirements)
            if not truth or not truth.get("prd_content"):
                raise ValueError(f"No approved PRD truth available for job {job_id}")

            self._truth_cache = truth
            truth_inputs = {
                "requirements": truth.get("requirements", ""),
                "prd": truth.get("prd_content", ""),
                "truth_prd_hash": truth.get("prd_hash", ""),
                "truth_requirements_hash": truth.get("requirements_hash", ""),
                "truth_prd_artifact_id": truth.get("prd_artifact_id"),
            }

            resume_from = None
            if isinstance(metadata, dict):
                resume_from = metadata.get("resume_from_stage")

            stage_order = [
                WorkflowStage.FEATURE_TREE,
                WorkflowStage.PLAN_GENERATION,
                WorkflowStage.ARCHITECTURE_DESIGN,
                WorkflowStage.UIUX_DESIGN,
                WorkflowStage.DEVELOPMENT,
                WorkflowStage.QA_TESTING,
                WorkflowStage.SECURITY_REVIEW,
                WorkflowStage.DOCUMENTATION,
                WorkflowStage.SUPPORT_DOCS,
                WorkflowStage.PM_REVIEW,
                WorkflowStage.DELIVERY,
            ]

            resume_stage = None
            if resume_from and resume_from in [s.value for s in stage_order]:
                resume_stage = WorkflowStage(resume_from)
                print(f"[MasterAgent] Resuming workflow from {resume_stage.value}")

            def should_run(stage: WorkflowStage) -> bool:
                if not resume_stage:
                    return True
                return stage_order.index(stage) >= stage_order.index(resume_stage)

            feature_tree_result = {}
            if should_run(WorkflowStage.FEATURE_TREE):
                feature_tree_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.FEATURE_TREE,
                    inputs={**truth_inputs},
                )

            feature_tree_content = await self._fetch_artifact_content(job_id, "feature_tree")
            if not feature_tree_content:
                feature_tree_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.FEATURE_TREE,
                    inputs={**truth_inputs},
                )
                feature_tree_content = await self._fetch_artifact_content(job_id, "feature_tree")

            plan_result = {}
            if should_run(WorkflowStage.PLAN_GENERATION):
                plan_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.PLAN_GENERATION,
                    inputs={
                        **truth_inputs,
                        "feature_tree": feature_tree_content or "",
                    },
                )

            plan_content = await self._fetch_artifact_content(job_id, "plan")
            if not plan_content:
                plan_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.PLAN_GENERATION,
                    inputs={
                        **truth_inputs,
                        "feature_tree": feature_tree_content or "",
                    },
                )
                plan_content = await self._fetch_artifact_content(job_id, "plan")

            architecture_result = {}
            if should_run(WorkflowStage.ARCHITECTURE_DESIGN):
                architecture_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.ARCHITECTURE_DESIGN,
                    inputs={
                        **truth_inputs,
                        "plan": plan_content or "",
                    },
                )

            architecture_content = await self._fetch_artifact_content(job_id, "architecture")
            if not architecture_content:
                architecture_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.ARCHITECTURE_DESIGN,
                    inputs={
                        **truth_inputs,
                        "plan": plan_content or "",
                    },
                )
                architecture_content = await self._fetch_artifact_content(job_id, "architecture")

            # Execute UI/UX design
            uiux_result = {}
            if should_run(WorkflowStage.UIUX_DESIGN):
                uiux_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.UIUX_DESIGN,
                    inputs={
                        **truth_inputs,
                        "architecture": architecture_content or "",
                    },
                )

            uiux_content = await self._fetch_artifact_content(job_id, "ui_ux")
            if not uiux_content:
                uiux_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.UIUX_DESIGN,
                    inputs={
                        **truth_inputs,
                        "architecture": architecture_content or "",
                    },
                )
                uiux_content = await self._fetch_artifact_content(job_id, "ui_ux")

            # Execute Development stage
            development_result = {}
            if should_run(WorkflowStage.DEVELOPMENT):
                development_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.DEVELOPMENT,
                    inputs={
                        **truth_inputs,
                        "architecture": architecture_content or "",
                        "ui_ux": uiux_content or "",
                    },
                )

            development_content = await self._fetch_artifact_content(job_id, "development")
            if not development_content:
                development_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.DEVELOPMENT,
                    inputs={
                        **truth_inputs,
                        "architecture": architecture_content or "",
                        "ui_ux": uiux_content or "",
                    },
                )
                development_content = await self._fetch_artifact_content(job_id, "development")

            # Execute QA Testing stage
            qa_result = {}
            if should_run(WorkflowStage.QA_TESTING):
                qa_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.QA_TESTING,
                    inputs={
                        **truth_inputs,
                        "development": development_content or "",
                        "architecture": architecture_content or "",
                    },
                )

            qa_content = await self._fetch_artifact_content(job_id, "qa")
            if not qa_content:
                qa_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.QA_TESTING,
                    inputs={
                        **truth_inputs,
                        "development": development_content or "",
                        "architecture": architecture_content or "",
                    },
                )
                qa_content = await self._fetch_artifact_content(job_id, "qa")

            # Execute Security Review stage
            security_result = {}
            if should_run(WorkflowStage.SECURITY_REVIEW):
                security_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.SECURITY_REVIEW,
                    inputs={
                        **truth_inputs,
                        "development": development_content or "",
                        "architecture": architecture_content or "",
                        "qa": qa_content or "",
                    },
                )

            security_content = await self._fetch_artifact_content(job_id, "security")
            if not security_content:
                security_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.SECURITY_REVIEW,
                    inputs={
                        **truth_inputs,
                        "development": development_content or "",
                        "architecture": architecture_content or "",
                        "qa": qa_content or "",
                    },
                )
                security_content = await self._fetch_artifact_content(job_id, "security")

            # Execute Documentation and Support stages in parallel after Security

            print(f"[MasterAgent] Starting parallel execution: documentation + support_docs")

            # Run documentation and support in parallel (gather awaits the coroutines)
            try:
                documentation_result = {}
                support_result = {}
                if should_run(WorkflowStage.DOCUMENTATION) or should_run(WorkflowStage.SUPPORT_DOCS):
                    documentation_result, support_result = await asyncio.gather(
                        self._execute_stage(
                            job_id=job_id,
                            project_id=project_id,
                            stage=WorkflowStage.DOCUMENTATION,
                            inputs={
                                **truth_inputs,
                                "development": development_content or "",
                                "architecture": architecture_content or "",
                                "qa": qa_content or "",
                                "security": security_content or "",
                            },
                        ),
                        self._execute_stage(
                            job_id=job_id,
                            project_id=project_id,
                            stage=WorkflowStage.SUPPORT_DOCS,
                            inputs={
                                **truth_inputs,
                                "development": development_content or "",
                                "architecture": architecture_content or "",
                                "qa": qa_content or "",
                                "security": security_content or "",
                            },
                        ),
                        return_exceptions=False,  # Raise exceptions immediately
                    )
                print(f"[MasterAgent] Parallel execution completed successfully")
            except Exception as e:
                print(f"[MasterAgent] ERROR in parallel execution: {e}")
                raise

            # Execute PM Review stage
            documentation_content = await self._fetch_artifact_content(job_id, "documentation")
            support_content = await self._fetch_artifact_content(job_id, "support_docs")
            if not documentation_content or not support_content:
                if should_run(WorkflowStage.DOCUMENTATION) or should_run(WorkflowStage.SUPPORT_DOCS):
                    documentation_result, support_result = await asyncio.gather(
                        self._execute_stage(
                            job_id=job_id,
                            project_id=project_id,
                            stage=WorkflowStage.DOCUMENTATION,
                            inputs={
                                **truth_inputs,
                                "development": development_content or "",
                                "architecture": architecture_content or "",
                                "qa": qa_content or "",
                                "security": security_content or "",
                            },
                        ),
                        self._execute_stage(
                            job_id=job_id,
                            project_id=project_id,
                            stage=WorkflowStage.SUPPORT_DOCS,
                            inputs={
                                **truth_inputs,
                                "development": development_content or "",
                                "architecture": architecture_content or "",
                                "qa": qa_content or "",
                                "security": security_content or "",
                            },
                        ),
                        return_exceptions=False,
                    )
                    documentation_content = await self._fetch_artifact_content(
                        job_id, "documentation"
                    )
                    support_content = await self._fetch_artifact_content(job_id, "support_docs")

            pm_review_result = {}
            if should_run(WorkflowStage.PM_REVIEW):
                pm_review_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.PM_REVIEW,
                    inputs={
                        **truth_inputs,
                        "development": development_content or "",
                        "architecture": architecture_content or "",
                        "qa": qa_content or "",
                        "security": security_content or "",
                        "documentation": documentation_content or "",
                        "support": support_content or "",
                    },
                )

            # Execute Delivery stage
            pm_review_content = await self._fetch_artifact_content(job_id, "pm_review")
            if not pm_review_content:
                pm_review_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.PM_REVIEW,
                    inputs={
                        **truth_inputs,
                        "development": development_content or "",
                        "architecture": architecture_content or "",
                        "qa": qa_content or "",
                        "security": security_content or "",
                        "documentation": documentation_content or "",
                        "support": support_content or "",
                    },
                )
                pm_review_content = await self._fetch_artifact_content(job_id, "pm_review")

            delivery_result = {}
            if should_run(WorkflowStage.DELIVERY):
                delivery_result = await self._execute_stage(
                    job_id=job_id,
                    project_id=project_id,
                    stage=WorkflowStage.DELIVERY,
                    inputs={
                        **truth_inputs,
                        "pm_review": pm_review_content or "",
                        "all_artifacts": {
                            "prd": prd_content,
                            "feature_tree": feature_tree_content or "",
                            "plan": plan_content or "",
                            "architecture": architecture_content or "",
                            "ui_ux": uiux_content or "",
                            "development": development_content or "",
                            "qa": qa_content or "",
                            "security": security_content or "",
                            "documentation": documentation_content or "",
                            "support": support_content or "",
                        },
                    },
                )

            # Transition to COMPLETED state
            await self.postgres.update_job_status(
                job_id=job_id, status="completed", workflow_stage=WorkflowStage.COMPLETED.value
            )

            return {
                "job_id": job_id,
                "status": "completed",
                "results": {
                    "feature_tree": feature_tree_result,
                    "plan": plan_result,
                    "architecture": architecture_result,
                    "ui_ux": uiux_result,
                    "development": development_result,
                    "qa": qa_result,
                    "security": security_result,
                    "documentation": documentation_result,
                    "support": support_result,
                    "pm_review": pm_review_result,
                    "delivery": delivery_result,
                },
            }
        except JobCanceledError as e:
            print(f"[MasterAgent] Job {job_id} canceled after approval: {str(e)}")
            await self.postgres.update_job_status(job_id=job_id, status="canceled")
            return {"job_id": job_id, "status": "canceled", "error": str(e)}
        except Exception as e:
            print(f"[MasterAgent] Job {job_id} failed after approval: {str(e)}")
            try:
                await publish_job_failed(job_id, str(e))
            except Exception as pub_err:
                print(f"[MasterAgent] Failed to publish job_failed event: {pub_err}")
            try:
                pool = await self.postgres.get_pool()
                async with pool.acquire() as conn:
                    stage_row = await conn.fetchrow(
                        "SELECT workflow_stage FROM jobs WHERE id = $1",
                        job_id,
                    )
                failed_stage = stage_row["workflow_stage"] if stage_row else None
                metadata_update = {"error": str(e)}
                if failed_stage and failed_stage != WorkflowStage.FAILED.value:
                    metadata_update["failed_stage"] = failed_stage

                await self.postgres.update_job_metadata(
                    job_id=job_id,
                    metadata=metadata_update,
                )
            except Exception as meta_err:
                print(f"[MasterAgent] Failed to persist job error metadata: {meta_err}")
            await self.postgres.update_job_status(
                job_id=job_id, status="failed", workflow_stage=WorkflowStage.FAILED.value
            )
            return {"job_id": job_id, "status": "failed", "error": str(e)}

    async def continue_after_change_request(self, job_id: str) -> Dict:
        """
        Regenerate PRD after a change request.

        Args:
            job_id: Job identifier

        Returns:
            Updated job results
        """
        try:
            project_id, requirements, metadata = await self._fetch_job_context(job_id)
            if not project_id:
                raise ValueError(f"Job {job_id} not found")
            if not requirements:
                raise ValueError(f"Job {job_id} missing requirements")

            prd_content, prd_artifact_id = await self._fetch_latest_prd(job_id)
            if not prd_content:
                raise ValueError(f"No prior PRD content available for job {job_id}")

            change_notes = metadata.get("change_request_notes") if isinstance(metadata, dict) else None
            change_requested_at = (
                metadata.get("changes_requested_at") if isinstance(metadata, dict) else None
            )

            prd_result = await self._execute_stage(
                job_id=job_id,
                project_id=project_id,
                stage=WorkflowStage.PRD_GENERATION,
                inputs={
                    "requirements": requirements,
                    "previous_prd": prd_content,
                    "previous_prd_artifact_id": prd_artifact_id,
                    "change_request_notes": change_notes,
                    "change_requested_at": change_requested_at,
                },
            )

            await self.postgres.update_job_status(
                job_id=job_id,
                status="waiting_for_approval",
                workflow_stage=WorkflowStage.WAITING_FOR_APPROVAL.value,
            )

            return {
                "job_id": job_id,
                "status": "waiting_for_approval",
                "results": {"prd": prd_result},
            }
        except JobCanceledError as e:
            print(f"[MasterAgent] Job {job_id} canceled during PRD revision: {str(e)}")
            await self.postgres.update_job_status(job_id=job_id, status="canceled")
            return {"job_id": job_id, "status": "canceled", "error": str(e)}
        except Exception as e:
            print(f"[MasterAgent] Job {job_id} failed during PRD revision: {str(e)}")
            try:
                await publish_job_failed(job_id, str(e))
            except Exception as pub_err:
                print(f"[MasterAgent] Failed to publish job_failed event: {pub_err}")
            try:
                await self.postgres.update_job_metadata(
                    job_id=job_id,
                    metadata={"error": str(e), "failed_stage": WorkflowStage.PRD_GENERATION.value},
                )
            except Exception as meta_err:
                print(f"[MasterAgent] Failed to persist job error metadata: {meta_err}")
            await self.postgres.update_job_status(
                job_id=job_id, status="failed", workflow_stage=WorkflowStage.FAILED.value
            )
            return {"job_id": job_id, "status": "failed", "error": str(e)}

    async def _fetch_project_and_prd(self, job_id: str) -> tuple[Optional[str], Optional[str]]:
        """Fetch project_id and latest PRD content for a job."""
        pool = await self.postgres.get_pool()
        async with pool.acquire() as conn:
            job_row = await conn.fetchrow("SELECT project_id FROM jobs WHERE id = $1", job_id)
            project_id = job_row["project_id"] if job_row else None

        # Prefer file store content when using file backend
        if settings.artifact_storage_backend == "file":
            try:
                store = get_artifact_store()
                if isinstance(store, FileArtifactStore):
                    artifact = await store.get_latest_by_type(job_id, "prd")
                    if artifact and artifact.get("content"):
                        return project_id, artifact["content"]
            except RuntimeError:
                pass

        # Fall back to PostgreSQL content
        async with pool.acquire() as conn:
            artifact_row = await conn.fetchrow(
                """
                SELECT content
                FROM artifacts
                WHERE job_id = $1 AND type = 'prd'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
            )
            if artifact_row and artifact_row.get("content"):
                content = artifact_row["content"]
                # If content is a file reference, try to resolve it
                if isinstance(content, str) and content.startswith("[file:") and content.endswith("]"):
                    try:
                        store = get_artifact_store()
                        if isinstance(store, FileArtifactStore):
                            artifact = await store.get_latest_by_type(job_id, "prd")
                            if artifact and artifact.get("content"):
                                return project_id, artifact["content"]
                    except RuntimeError:
                        pass
                return project_id, content

            task_row = await conn.fetchrow(
                """
                SELECT output_data->>'prd_content' AS prd_content
                FROM tasks
                WHERE job_id = $1 AND task_type = $2
                ORDER BY completed_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
                WorkflowStage.PRD_GENERATION.value,
            )
            prd_content = task_row["prd_content"] if task_row else None

        return project_id, prd_content

    async def _fetch_job_context(self, job_id: str) -> tuple[Optional[str], Optional[str], Dict]:
        """Fetch project_id, requirements, and metadata for a job."""
        pool = await self.postgres.get_pool()
        async with pool.acquire() as conn:
            job_row = await conn.fetchrow(
                "SELECT project_id, metadata FROM jobs WHERE id = $1",
                job_id,
            )
            if not job_row:
                return None, None, {}
            metadata = job_row.get("metadata") or {}
            if isinstance(metadata, str):
                try:
                    import json

                    metadata = json.loads(metadata)
                except Exception:
                    metadata = {}
            requirements = metadata.get("requirements") if isinstance(metadata, dict) else None
        return job_row.get("project_id"), requirements, metadata

    async def _fetch_job_truth(self, job_id: str) -> Optional[Dict[str, str]]:
        """Fetch canonical truth (requirements + approved PRD) for a job."""
        pool = await self.postgres.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT job_id, requirements, requirements_hash, prd_content, prd_hash, prd_artifact_id
                FROM job_truth
                WHERE job_id = $1
                """,
                job_id,
            )
        if not row:
            return None
        return {
            "job_id": row["job_id"],
            "requirements": row["requirements"],
            "requirements_hash": row["requirements_hash"],
            "prd_content": row["prd_content"],
            "prd_hash": row["prd_hash"],
            "prd_artifact_id": row["prd_artifact_id"],
        }

    async def _backfill_job_truth(
        self, job_id: str, requirements: Optional[str]
    ) -> Optional[Dict[str, str]]:
        """Backfill job truth if missing (uses latest PRD + requirements)."""
        prd_content, prd_artifact_id = await self._fetch_latest_prd(job_id)
        if not prd_content:
            return None
        req_text = (requirements or "").strip()

        pool = await self.postgres.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO job_truth (
                    job_id, requirements, requirements_hash, prd_content, prd_hash, prd_artifact_id, approved_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (job_id) DO UPDATE
                SET requirements = EXCLUDED.requirements,
                    requirements_hash = EXCLUDED.requirements_hash,
                    prd_content = EXCLUDED.prd_content,
                    prd_hash = EXCLUDED.prd_hash,
                    prd_artifact_id = EXCLUDED.prd_artifact_id,
                    approved_at = NOW(),
                    updated_at = NOW()
                """,
                job_id,
                req_text,
                hash_text(req_text),
                prd_content,
                hash_text(prd_content),
                prd_artifact_id,
            )

        return {
            "job_id": job_id,
            "requirements": req_text,
            "requirements_hash": hash_text(req_text),
            "prd_content": prd_content,
            "prd_hash": hash_text(prd_content),
            "prd_artifact_id": prd_artifact_id,
        }

    async def _fetch_latest_prd(self, job_id: str) -> tuple[Optional[str], Optional[str]]:
        """Fetch latest PRD content and artifact ID for a job."""
        if settings.artifact_storage_backend == "file":
            try:
                store = get_artifact_store()
                if isinstance(store, FileArtifactStore):
                    artifact = await store.get_latest_by_type(job_id, "prd")
                    if artifact:
                        return artifact.get("content"), artifact.get("id")
            except RuntimeError:
                pass

        pool = await self.postgres.get_pool()
        async with pool.acquire() as conn:
            prd_row = await conn.fetchrow(
                """
                SELECT id, content, metadata
                FROM artifacts
                WHERE job_id = $1 AND type = 'prd'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
            )
            if not prd_row:
                return None, None
            content = prd_row.get("content")
            metadata = prd_row.get("metadata") or {}
            if isinstance(content, str) and content.startswith("[file:") and content.endswith("]"):
                file_path = metadata.get("_file_path") if isinstance(metadata, dict) else None
                if file_path:
                    try:
                        with open(file_path, "r") as f:
                            content = f.read()
                    except Exception:
                        pass
            return content, prd_row.get("id")

    async def _fetch_artifact_content(self, job_id: str, artifact_type: str) -> Optional[str]:
        """Fetch artifact content by type for a job."""
        if settings.artifact_storage_backend == "file":
            try:
                store = get_artifact_store()
                if isinstance(store, FileArtifactStore):
                    artifact = await store.get_latest_by_type(job_id, artifact_type)
                    if artifact and artifact.get("content"):
                        return artifact["content"]
            except RuntimeError:
                pass

        pool = await self.postgres.get_pool()
        async with pool.acquire() as conn:
            artifact_row = await conn.fetchrow(
                """
                SELECT content
                FROM artifacts
                WHERE job_id = $1 AND type = $2
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
                artifact_type,
            )
            if not artifact_row:
                return None
            content = artifact_row["content"]
            if isinstance(content, str) and content.startswith("[file:") and content.endswith("]"):
                try:
                    store = get_artifact_store()
                    if isinstance(store, FileArtifactStore):
                        artifact = await store.get_latest_by_type(job_id, artifact_type)
                        if artifact and artifact.get("content"):
                            return artifact["content"]
                except RuntimeError:
                    pass
            return content

    def _truth_text(self) -> str:
        if not self._truth_cache:
            return ""
        requirements = self._truth_cache.get("requirements") or ""
        prd_content = self._truth_cache.get("prd_content") or ""
        return f"{requirements}\n\n{prd_content}".strip()

    def _build_truth_config(self) -> Dict[str, str]:
        if not self._truth_cache:
            return {}
        return {
            "truth_prd_hash": self._truth_cache.get("prd_hash", ""),
            "truth_requirements_hash": self._truth_cache.get("requirements_hash", ""),
            "truth_prd_artifact_id": self._truth_cache.get("prd_artifact_id") or "",
        }

    def _coerce_result_content(self, result: Dict, artifact_type: str) -> Optional[str]:
        if not isinstance(result, dict):
            return None
        candidate = result.get(artifact_type)
        if candidate is None:
            return None
        if isinstance(candidate, str):
            return candidate
        try:
            return json.dumps(candidate, indent=2, sort_keys=True)
        except Exception:
            return str(candidate)

    async def _validate_alignment(
        self, job_id: str, stage: WorkflowStage, result: Dict
    ) -> None:
        if not self._truth_cache:
            return
        artifact_type = STAGE_ARTIFACT_TYPES.get(stage)
        if not artifact_type:
            return

        truth_text = self._truth_text()
        if not truth_text:
            return

        artifact_content = await self._fetch_artifact_content(job_id, artifact_type)
        if not artifact_content:
            artifact_content = self._coerce_result_content(result, artifact_type)
        if not artifact_content:
            raise RuntimeError(
                f"Alignment check failed: missing {artifact_type} content for {stage.value}"
            )

        check = alignment_check(
            truth_text=truth_text,
            artifact_text=artifact_content,
            min_matches=settings.truth_alignment_min_matches,
            threshold=settings.truth_alignment_threshold,
        )

        if check.get("status") == "fail":
            await self.postgres.update_job_metadata(
                job_id=job_id,
                metadata={
                    "alignment_failure": {
                        "stage": stage.value,
                        "artifact_type": artifact_type,
                        "score": check.get("score"),
                        "matches": check.get("matches", []),
                        "keywords": check.get("keywords", []),
                    }
                },
            )
            raise RuntimeError(
                f"Alignment check failed for {stage.value} (score={check.get('score')})"
            )

    async def _execute_stage(
        self, job_id: str, project_id: str, stage: WorkflowStage, inputs: Dict
    ) -> Dict:
        """
        Execute a workflow stage by dispatching to the appropriate agent.

        Args:
            job_id: Job identifier
            stage: Workflow stage to execute
            inputs: Input data for the stage

        Returns:
            Stage output data
        """
        agent_id = self.workflow.get_agent_for_stage(stage)
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        print(f"[MasterAgent] Executing stage {stage.value} with agent {agent_id}")

        # Publish stage started event
        try:
            await publish_stage_started(job_id, stage.value, agent_id)
        except Exception as e:
            print(f"[MasterAgent] Failed to publish stage_started event: {e}")

        # Update job status
        await self.postgres.update_job_status(
            job_id=job_id, status="in_progress", workflow_stage=stage.value
        )

        # Create task
        task_data = {
            "task_id": task_id,
            "job_id": job_id,
            "project_id": project_id,
            "agent_type": agent_id,
            "stage": stage.value,
            "inputs": inputs,
            "priority": 5,
        }
        if self._truth_cache:
            task_data["config"] = self._build_truth_config()

        queue_name = "agent_bus:tasks"

        # Create task in database
        await self.postgres.create_task(
            task_id=task_id,
            job_id=job_id,
            agent_id=agent_id,
            task_type=stage.value,
            input_data=inputs,
        )
        print(f"[MasterAgent] Created task {task_id} in database for stage {stage.value}")

        # Enqueue task to Redis
        await self.redis.enqueue_task(queue_name, task_data)
        print(f"[MasterAgent] Enqueued task {task_id} to {queue_name}")

        try:
            # Wait for completion
            print(f"[MasterAgent] Waiting for task {task_id} to complete...")
            result = await self._wait_for_task(task_id, job_id=job_id, timeout=3600)
            print(f"[MasterAgent] Task {task_id} completed with result type: {type(result)}")

            # Publish stage completed event
            try:
                await publish_stage_completed(job_id, stage.value)
            except Exception as e:
                print(f"[MasterAgent] Failed to publish stage_completed event: {e}")

            # Normalize failure signaling (worker writes a result key even on crash)
            if isinstance(result, dict) and result.get("success") is False:
                raise RuntimeError(result.get("error") or f"Task {task_id} failed")
            if isinstance(result, dict) and result.get("error"):
                raise RuntimeError(result.get("error"))

            await self._validate_alignment(job_id, stage, result)
            return result
        except JobCanceledError:
            raise
        except Exception as e:
            try:
                await self.postgres.update_job_metadata(
                    job_id=job_id,
                    metadata={"failed_stage": stage.value, "error": str(e)},
                )
            except Exception as meta_err:
                print(f"[MasterAgent] Failed to persist job failure metadata: {meta_err}")
            raise

    async def _wait_for_task(self, task_id: str, job_id: str, timeout: int = 3600) -> Dict:
        """
        Wait for a task to complete.

        Args:
            task_id: Task identifier
            timeout: Maximum wait time in seconds

        Returns:
            Task result
        """
        # Poll Redis for result
        start_time = datetime.now()
        result_key = f"agent_bus:results:{task_id}"

        while (datetime.now() - start_time).seconds < timeout:
            result = await self.redis.get(result_key)
            if result:
                import json

                return json.loads(result)

            # Stop waiting if job was canceled
            try:
                pool = await self.postgres.get_pool()
                async with pool.acquire() as conn:
                    status = await conn.fetchval(
                        "SELECT status FROM jobs WHERE id = $1",
                        job_id,
                    )
                if status == "canceled":
                    raise JobCanceledError(f"Job {job_id} canceled")
            except JobCanceledError:
                raise
            except Exception:
                pass

            await asyncio.sleep(1)

        raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")


class JobCanceledError(Exception):
    """Raised when a job is canceled mid-flight."""

    pass
