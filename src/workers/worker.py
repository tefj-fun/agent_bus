"""Worker process for executing agent tasks."""

import asyncio
import json
from typing import Dict, Optional

from ..agents.base import BaseAgent, AgentContext, AgentTask
from ..agents.prd_agent import PRDAgent
from ..agents.technical_writer import TechnicalWriter
from ..agents.support_engineer import SupportEngineer
from ..agents.product_manager import ProductManager
from ..agents.project_manager import ProjectManager
from ..agents.memory_agent import MemoryAgent
from ..agents.plan_agent import PlanAgent
from ..agents.architect_agent import ArchitectAgent
from ..agents.uiux_agent import UIUXAgent
from ..agents.developer_agent import DeveloperAgent
from ..agents.qa_agent import QAAgent
from ..agents.security_agent import SecurityAgent
# TODO: Import other specialized agents as they are implemented
# etc.

from ..infrastructure.redis_client import RedisClient, redis_client
from ..infrastructure.postgres_client import PostgresClient, postgres_client
from ..infrastructure.anthropic_client import anthropic_client
from ..skills.manager import SkillsManager
from ..config import settings


class AgentWorker:
    """Worker process that polls Redis and executes agent tasks."""

    def __init__(self, worker_type: str = "cpu"):
        self.worker_type = worker_type
        self.redis = redis_client
        self.postgres = postgres_client
        self.anthropic = anthropic_client
        self.skills_manager = SkillsManager(settings.skills_directory)
        self.agent_registry = self._register_agents()

    def _register_agents(self) -> Dict[str, type]:
        """Register all available agent types."""
        return {
            "prd_agent": PRDAgent,
            "tech_writer": TechnicalWriter,
            "support_engineer": SupportEngineer,
            "product_manager": ProductManager,
            "project_manager": ProjectManager,
            "memory_agent": MemoryAgent,
            "plan_agent": PlanAgent,
            "architect_agent": ArchitectAgent,
            "uiux_agent": UIUXAgent,
            "developer_agent": DeveloperAgent,
            "qa_agent": QAAgent,
            "security_agent": SecurityAgent,
            # TODO: Register other agents
        }

    async def run(self):
        """Main worker loop."""
        queue_name = (
            "agent_bus:tasks:gpu" if self.worker_type == "gpu"
            else "agent_bus:tasks:cpu"
        )

        print(f"Worker started: type={self.worker_type} queue={queue_name}")

        # Connect to infrastructure
        await self.redis.connect()
        await self.postgres.connect()

        while True:
            try:
                # Poll for task (blocking with 5s timeout)
                task = await self.redis.dequeue_task(queue_name, timeout=5)

                if task:
                    print(f"Received task: {task.get('task_id')}")
                    await self._execute_task(task)

            except Exception as e:
                print(f"Worker error: {e}")
                await asyncio.sleep(1)

    async def _execute_task(self, task_dict: Dict):
        """
        Execute a single agent task.

        Args:
            task_dict: Task data from queue
        """
        task_id = task_dict["task_id"]
        agent_type = task_dict["agent_type"]

        # Update task status to RUNNING
        await self.postgres.update_task_status(task_id, "running")

        try:
            # Get agent class
            AgentClass = self.agent_registry.get(agent_type)
            if not AgentClass:
                raise ValueError(f"Unknown agent type: {agent_type}")

            # Create agent context
            context = AgentContext(
                project_id=task_dict.get("project_id", "unknown"),
                job_id=task_dict["job_id"],
                session_key=f"session:{task_id}",
                workspace_dir=f"/workspace/{task_dict['job_id']}",
                redis_client=await self.redis.get_client(),
                db_pool=await self.postgres.get_pool(),
                anthropic_client=self.anthropic,
                skills_manager=self.skills_manager,
                config=task_dict.get("config", {})
            )

            # Instantiate and execute agent
            agent = AgentClass(context)

            # Create AgentTask
            agent_task = AgentTask(
                task_id=task_id,
                task_type=agent_type,
                input_data=task_dict["inputs"],
                dependencies=task_dict.get("dependencies", []),
                priority=task_dict.get("priority", 5),
                metadata=task_dict.get("metadata", {})
            )

            # Execute
            result = await agent.execute(agent_task)

            if not result.success:
                # Persist failure details
                await self.postgres.update_task_status(
                    task_id=task_id,
                    status="failed",
                    error=result.error or "Agent reported failure"
                )
                # Also store output (may contain partials) for master/debug
                await self.redis.set_with_expiry(
                    f"agent_bus:results:{task_id}",
                    json.dumps({
                        "success": False,
                        "error": result.error or "Agent reported failure",
                        **(result.output or {}),
                    }),
                    3600,
                )
                print(f"Task {task_id} failed (agent reported failure)")
                return

            # Save success result
            await self.postgres.update_task_status(
                task_id=task_id,
                status="completed",
                output_data=result.output
            )

            # Store result in Redis for master agent
            await self.redis.set_with_expiry(
                f"agent_bus:results:{task_id}",
                json.dumps(result.output),
                3600  # 1 hour TTL
            )

            print(f"Task {task_id} completed successfully")

        except Exception as e:
            print(f"Task {task_id} failed: {str(e)}")

            await self.postgres.update_task_status(
                task_id=task_id,
                status="failed",
                error=str(e)
            )

            # Ensure master agent doesn't hang forever waiting for a result key
            await self.redis.set_with_expiry(
                f"agent_bus:results:{task_id}",
                json.dumps({"error": str(e), "success": False, "task_id": task_id}),
                3600,
            )


async def main():
    """Main entry point for worker."""
    worker = AgentWorker(worker_type=settings.worker_type)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
