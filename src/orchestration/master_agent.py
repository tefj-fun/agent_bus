"""Master Agent for orchestrating the SWE engineering workflow."""

import asyncio
import uuid
from typing import Dict, List, Optional
from datetime import datetime

from .workflow import WorkflowStateMachine, WorkflowStage
from ..infrastructure.redis_client import RedisClient
from ..infrastructure.postgres_client import PostgresClient
from ..infrastructure.anthropic_client import anthropic_client
from ..skills.manager import SkillsManager
from ..agents.base import AgentContext
from ..config import settings


class MasterAgent:
    """
    Master orchestration agent (SWE Engineering Manager).

    Coordinates all specialized agents through the workflow pipeline.
    """

    def __init__(
        self,
        redis_client: RedisClient,
        postgres_client: PostgresClient,
        skills_manager: SkillsManager
    ):
        self.redis = redis_client
        self.postgres = postgres_client
        self.anthropic = anthropic_client
        self.skills_manager = skills_manager
        self.workflow = WorkflowStateMachine()

    async def orchestrate_project(
        self,
        project_id: str,
        requirements: str
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
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        await self.postgres.create_job(
            job_id=job_id,
            project_id=project_id,
            workflow_stage=WorkflowStage.INITIALIZATION.value
        )

        print(f"[MasterAgent] Starting job {job_id} for project {project_id}")

        try:
            # Stage 1: PRD Generation
            prd_result = await self._execute_stage(
                job_id=job_id,
                stage=WorkflowStage.PRD_GENERATION,
                inputs={"requirements": requirements}
            )

            # Stage 2: Architecture Design
            arch_result = await self._execute_stage(
                job_id=job_id,
                stage=WorkflowStage.ARCHITECTURE_DESIGN,
                inputs={"prd": prd_result}
            )

            # Stage 3: UI/UX Design
            uiux_result = await self._execute_stage(
                job_id=job_id,
                stage=WorkflowStage.UIUX_DESIGN,
                inputs={"architecture": arch_result, "prd": prd_result}
            )

            # Stage 4: Development
            dev_result = await self._execute_stage(
                job_id=job_id,
                stage=WorkflowStage.DEVELOPMENT,
                inputs={
                    "architecture": arch_result,
                    "design_system": uiux_result,
                    "prd": prd_result
                }
            )

            # Stage 5: Parallel Execution (QA, Security, Docs)
            parallel_results = await asyncio.gather(
                self._execute_stage(
                    job_id=job_id,
                    stage=WorkflowStage.QA_TESTING,
                    inputs={"code": dev_result}
                ),
                self._execute_stage(
                    job_id=job_id,
                    stage=WorkflowStage.SECURITY_REVIEW,
                    inputs={"code": dev_result}
                ),
                self._execute_stage(
                    job_id=job_id,
                    stage=WorkflowStage.DOCUMENTATION,
                    inputs={"code": dev_result, "architecture": arch_result}
                ),
                self._execute_stage(
                    job_id=job_id,
                    stage=WorkflowStage.SUPPORT_DOCS,
                    inputs={"code": dev_result, "user_docs": None}
                )
            )

            # Stage 6: PM Review
            pm_result = await self._execute_stage(
                job_id=job_id,
                stage=WorkflowStage.PM_REVIEW,
                inputs={
                    "development": dev_result,
                    "qa": parallel_results[0],
                    "security": parallel_results[1],
                    "documentation": parallel_results[2],
                    "support": parallel_results[3]
                }
            )

            # Stage 7: Delivery
            await self._execute_stage(
                job_id=job_id,
                stage=WorkflowStage.DELIVERY,
                inputs={"all_outputs": pm_result}
            )

            # Mark as completed
            await self.postgres.update_job_status(
                job_id=job_id,
                status="completed",
                workflow_stage=WorkflowStage.COMPLETED.value
            )

            print(f"[MasterAgent] Job {job_id} completed successfully")

            return {
                "job_id": job_id,
                "status": "completed",
                "results": {
                    "prd": prd_result,
                    "architecture": arch_result,
                    "design": uiux_result,
                    "development": dev_result,
                    "qa": parallel_results[0],
                    "security": parallel_results[1],
                    "documentation": parallel_results[2],
                    "support": parallel_results[3],
                    "pm_review": pm_result
                }
            }

        except Exception as e:
            print(f"[MasterAgent] Job {job_id} failed: {str(e)}")

            await self.postgres.update_job_status(
                job_id=job_id,
                status="failed",
                workflow_stage=WorkflowStage.FAILED.value
            )

            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e)
            }

    async def _execute_stage(
        self,
        job_id: str,
        stage: WorkflowStage,
        inputs: Dict
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

        # Update job status
        await self.postgres.update_job_status(
            job_id=job_id,
            status="in_progress",
            workflow_stage=stage.value
        )

        # Create task
        task_data = {
            "task_id": task_id,
            "job_id": job_id,
            "agent_type": agent_id,
            "stage": stage.value,
            "inputs": inputs,
            "priority": 5
        }

        # Detect ML/CV workload and route appropriately
        if self._is_ml_workload(inputs):
            task_data["resource_requirements"] = {
                "gpu": True,
                "gpu_type": "nvidia-tesla-v100",
                "memory": "32Gi"
            }
            queue_name = "agent_bus:tasks:gpu"
        else:
            queue_name = "agent_bus:tasks:cpu"

        # Create task in database
        await self.postgres.create_task(
            task_id=task_id,
            job_id=job_id,
            agent_id=agent_id,
            task_type=stage.value,
            input_data=inputs
        )

        # Enqueue task to Redis
        await self.redis.enqueue_task(queue_name, task_data)

        # Wait for completion
        result = await self._wait_for_task(task_id, timeout=3600)

        return result

    def _is_ml_workload(self, inputs: Dict) -> bool:
        """
        Detect if this is an ML/CV workload that needs GPU.

        Args:
            inputs: Stage input data

        Returns:
            True if ML/CV workload detected
        """
        ml_keywords = [
            "machine learning", "neural network", "deep learning",
            "computer vision", "image processing", "model training",
            "tensorflow", "pytorch", "cv", "ml pipeline", "ai model"
        ]

        text = str(inputs).lower()
        return any(keyword in text for keyword in ml_keywords)

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
                return eval(result)  # TODO: Use json.loads

            await asyncio.sleep(1)

        raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
