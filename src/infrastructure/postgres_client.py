"""PostgreSQL client for state persistence."""

import asyncpg
from typing import Optional
from ..config import settings


class PostgresClient:
    """PostgreSQL client wrapper for agent_bus."""

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> asyncpg.Pool:
        """Create connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                settings.postgres_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
        return self._pool

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def get_pool(self) -> asyncpg.Pool:
        """Get connection pool."""
        if self._pool is None:
            await self.connect()
        return self._pool

    async def create_job(
        self,
        job_id: str,
        project_id: str,
        workflow_stage: str = "initialization"
    ) -> None:
        """Create a new job."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO jobs (id, project_id, status, workflow_stage)
                VALUES ($1, $2, 'created', $3)
                """,
                job_id,
                project_id,
                workflow_stage
            )

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        workflow_stage: Optional[str] = None
    ) -> None:
        """Update job status."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            if workflow_stage:
                await conn.execute(
                    """
                    UPDATE jobs
                    SET status = $2, workflow_stage = $3
                    WHERE id = $1
                    """,
                    job_id,
                    status,
                    workflow_stage
                )
            else:
                await conn.execute(
                    """
                    UPDATE jobs
                    SET status = $2
                    WHERE id = $1
                    """,
                    job_id,
                    status
                )

    async def create_task(
        self,
        task_id: str,
        job_id: str,
        agent_id: str,
        task_type: str,
        input_data: dict,
        dependencies: list = None,
        priority: int = 5
    ) -> None:
        """Create a new task."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (
                    id, job_id, agent_id, task_type, status,
                    priority, input_data, dependencies
                )
                VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7)
                """,
                task_id,
                job_id,
                agent_id,
                task_type,
                priority,
                input_data,
                dependencies or []
            )

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        output_data: Optional[dict] = None,
        error: Optional[str] = None
    ) -> None:
        """Update task status."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            if output_data:
                await conn.execute(
                    """
                    UPDATE tasks
                    SET status = $2, output_data = $3, completed_at = NOW()
                    WHERE id = $1
                    """,
                    task_id,
                    status,
                    output_data
                )
            elif error:
                await conn.execute(
                    """
                    UPDATE tasks
                    SET status = $2, error = $3
                    WHERE id = $1
                    """,
                    task_id,
                    status,
                    error
                )
            else:
                await conn.execute(
                    """
                    UPDATE tasks
                    SET status = $2
                    WHERE id = $1
                    """,
                    task_id,
                    status
                )


# Global PostgreSQL client instance
postgres_client = PostgresClient()
