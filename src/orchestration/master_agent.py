"""Master Agent for orchestrating the SWE engineering workflow."""

import asyncio
import uuid
from typing import Dict, Optional
from datetime import datetime

from .workflow import WorkflowStateMachine, WorkflowStage
from ..infrastructure.redis_client import RedisClient
from ..infrastructure.postgres_client import PostgresClient
from ..infrastructure.anthropic_client import anthropic_client
from ..skills.manager import SkillsManager
from ..api.routes.events import publish_stage_started, publish_stage_completed, publish_job_failed, publish_job_started


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
            project_id, prd_content = await self._fetch_project_and_prd(job_id)
            if not project_id:
                raise ValueError(f"Job {job_id} not found")
            if not prd_content:
                raise ValueError(f"No PRD content available for job {job_id}")

            # Execute plan generation
            plan_result = await self._execute_stage(
                job_id=job_id,
                project_id=project_id,
                stage=WorkflowStage.PLAN_GENERATION,
                inputs={"prd": prd_content},
            )

            # Execute architecture design
            plan_content = await self._fetch_artifact_content(job_id, "plan")
            architecture_result = await self._execute_stage(
                job_id=job_id,
                project_id=project_id,
                stage=WorkflowStage.ARCHITECTURE_DESIGN,
                inputs={"prd": prd_content, "plan": plan_content or ""},
            )

            # Execute UI/UX design
            architecture_content = await self._fetch_artifact_content(job_id, "architecture")
            uiux_result = await self._execute_stage(
                job_id=job_id,
                project_id=project_id,
                stage=WorkflowStage.UIUX_DESIGN,
                inputs={"architecture": architecture_content or "", "prd": prd_content},
            )

            # Execute Development stage
            uiux_content = await self._fetch_artifact_content(job_id, "ui_ux")
            development_result = await self._execute_stage(
                job_id=job_id,
                project_id=project_id,
                stage=WorkflowStage.DEVELOPMENT,
                inputs={
                    "architecture": architecture_content or "",
                    "ui_ux": uiux_content or "",
                    "prd": prd_content,
                },
            )

            # Execute QA Testing stage
            development_content = await self._fetch_artifact_content(job_id, "development")
            qa_result = await self._execute_stage(
                job_id=job_id,
                project_id=project_id,
                stage=WorkflowStage.QA_TESTING,
                inputs={
                    "development": development_content or "",
                    "architecture": architecture_content or "",
                    "prd": prd_content,
                },
            )

            # Execute Security Review stage
            qa_content = await self._fetch_artifact_content(job_id, "qa")
            security_result = await self._execute_stage(
                job_id=job_id,
                project_id=project_id,
                stage=WorkflowStage.SECURITY_REVIEW,
                inputs={
                    "development": development_content or "",
                    "architecture": architecture_content or "",
                    "qa": qa_content or "",
                    "prd": prd_content,
                },
            )

            # Execute Documentation and Support stages in parallel after Security
            security_content = await self._fetch_artifact_content(job_id, "security")

            print(f"[MasterAgent] Starting parallel execution: documentation + support_docs")

            # Run documentation and support in parallel (gather awaits the coroutines)
            try:
                documentation_result, support_result = await asyncio.gather(
                    self._execute_stage(
                        job_id=job_id,
                        project_id=project_id,
                        stage=WorkflowStage.DOCUMENTATION,
                        inputs={
                            "development": development_content or "",
                            "architecture": architecture_content or "",
                            "qa": qa_content or "",
                            "security": security_content or "",
                            "prd": prd_content,
                        },
                    ),
                    self._execute_stage(
                        job_id=job_id,
                        project_id=project_id,
                        stage=WorkflowStage.SUPPORT_DOCS,
                        inputs={
                            "development": development_content or "",
                            "architecture": architecture_content or "",
                            "qa": qa_content or "",
                            "security": security_content or "",
                            "prd": prd_content,
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
            support_content = await self._fetch_artifact_content(job_id, "support")
            pm_review_result = await self._execute_stage(
                job_id=job_id,
                project_id=project_id,
                stage=WorkflowStage.PM_REVIEW,
                inputs={
                    "development": development_content or "",
                    "architecture": architecture_content or "",
                    "qa": qa_content or "",
                    "security": security_content or "",
                    "documentation": documentation_content or "",
                    "support": support_content or "",
                    "prd": prd_content,
                },
            )

            # Execute Delivery stage
            pm_review_content = await self._fetch_artifact_content(job_id, "pm_review")
            delivery_result = await self._execute_stage(
                job_id=job_id,
                project_id=project_id,
                stage=WorkflowStage.DELIVERY,
                inputs={
                    "pm_review": pm_review_content or "",
                    "all_artifacts": {
                        "prd": prd_content,
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

    async def _fetch_project_and_prd(self, job_id: str) -> tuple[Optional[str], Optional[str]]:
        """Fetch project_id and latest PRD content for a job."""
        pool = await self.postgres.get_pool()
        async with pool.acquire() as conn:
            job_row = await conn.fetchrow("SELECT project_id FROM jobs WHERE id = $1", job_id)
            project_id = job_row["project_id"] if job_row else None

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
                return project_id, artifact_row["content"]

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

    async def _fetch_artifact_content(self, job_id: str, artifact_type: str) -> Optional[str]:
        """Fetch artifact content by type for a job."""
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
            return artifact_row["content"] if artifact_row else None

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
            result = await self._wait_for_task(task_id, timeout=3600)
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

            return result
        except Exception as e:
            try:
                await self.postgres.update_job_metadata(
                    job_id=job_id,
                    metadata={"failed_stage": stage.value, "error": str(e)},
                )
            except Exception as meta_err:
                print(f"[MasterAgent] Failed to persist job failure metadata: {meta_err}")
            raise

    async def _wait_for_task(self, task_id: str, timeout: int = 3600) -> Dict:
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

            await asyncio.sleep(1)

        raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
