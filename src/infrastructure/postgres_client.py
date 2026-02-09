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
                settings.postgres_url, min_size=2, max_size=10, command_timeout=60
            )
            # Best-effort schema bootstrap for long-lived volumes where init scripts won't re-run.
            try:
                await self.ensure_schema()
            except Exception:
                pass
        return self._pool

    async def ensure_schema(self) -> None:
        """Ensure required tables/functions exist.

        Docker Postgres init scripts only run on first volume creation. When the schema
        evolves, existing volumes can miss tables and cause runtime failures (e.g. HITL approval).
        This is a lightweight, idempotent bootstrap.
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                -- Ensure updated_at trigger function exists
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql';

                -- Canonical job truth table (requirements + approved PRD)
                CREATE TABLE IF NOT EXISTS job_truth (
                    job_id VARCHAR(255) PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
                    requirements TEXT NOT NULL,
                    requirements_hash VARCHAR(64) NOT NULL,
                    prd_content TEXT NOT NULL,
                    prd_hash VARCHAR(64) NOT NULL,
                    prd_artifact_id VARCHAR(255),
                    approved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_job_truth_prd_hash ON job_truth(prd_hash);

                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger WHERE tgname = 'update_job_truth_updated_at'
                    ) THEN
                        CREATE TRIGGER update_job_truth_updated_at BEFORE UPDATE ON job_truth
                            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                    END IF;
                END;
                $$;

                -- Module catalog table (global reusable modules)
                CREATE TABLE IF NOT EXISTS module_catalog (
                    id SERIAL PRIMARY KEY,
                    module_id VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    capabilities JSONB DEFAULT '[]'::jsonb,
                    owner VARCHAR(255),
                    description TEXT,
                    version INTEGER DEFAULT 1,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_module_catalog_module_id ON module_catalog(module_id);
                CREATE INDEX IF NOT EXISTS idx_module_catalog_active ON module_catalog(active);

                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger WHERE tgname = 'update_module_catalog_updated_at'
                    ) THEN
                        CREATE TRIGGER update_module_catalog_updated_at BEFORE UPDATE ON module_catalog
                            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
                    END IF;
                END;
                $$;
                """
            )

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
        status: str = "created",
        workflow_stage: str = "initialization",
    ) -> None:
        """Create a new job."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO jobs (id, project_id, status, workflow_stage)
                VALUES ($1, $2, $3, $4)
                """,
                job_id,
                project_id,
                status,
                workflow_stage,
            )

    async def update_job_status(
        self, job_id: str, status: str, workflow_stage: Optional[str] = None
    ) -> bool:
        """Update job status.

        Returns:
            True if a row was updated, False if the job did not exist.
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            if workflow_stage:
                res = await conn.execute(
                    """
                    UPDATE jobs
                    SET status = $2, workflow_stage = $3
                    WHERE id = $1
                    """,
                    job_id,
                    status,
                    workflow_stage,
                )
            else:
                res = await conn.execute(
                    """
                    UPDATE jobs
                    SET status = $2
                    WHERE id = $1
                    """,
                    job_id,
                    status,
                )

            # asyncpg returns strings like "UPDATE 1"
            try:
                return int(res.split()[-1]) > 0
            except Exception:
                return False

    async def update_job_metadata(self, job_id: str, metadata: dict) -> bool:
        """Merge metadata into the job's metadata JSON.

        Returns:
            True if a row was updated, False if the job did not exist.
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            import json

            res = await conn.execute(
                """
                UPDATE jobs
                SET metadata = COALESCE(metadata, '{}'::jsonb) || $2::jsonb
                WHERE id = $1
                """,
                job_id,
                json.dumps(metadata),
            )
            try:
                return int(res.split()[-1]) > 0
            except Exception:
                return False

    async def get_job_status(self, job_id: str) -> Optional[str]:
        """Get current job status, or None if the job does not exist."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT status FROM jobs WHERE id = $1", job_id)

    async def job_exists(self, job_id: str) -> bool:
        """Return True if job exists, otherwise False."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval("SELECT 1 FROM jobs WHERE id = $1", job_id) is not None

    async def claim_next_job(
        self, from_status: str = "queued", to_status: str = "orchestrating"
    ) -> Optional[dict]:
        """Atomically claim the next job of a given status.

        Returns:
            Job row as dict, or None if no jobs.
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                WITH next_job AS (
                  SELECT id
                  FROM jobs
                  WHERE status = '{from_status}'
                  ORDER BY created_at ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE jobs j
                SET status = '{to_status}', updated_at = NOW()
                FROM next_job
                WHERE j.id = next_job.id
                RETURNING j.id, j.project_id, j.status, j.workflow_stage, j.metadata
                """
            )
            return dict(row) if row else None

    async def create_task(
        self,
        task_id: str,
        job_id: str,
        agent_id: str,
        task_type: str,
        input_data: dict,
        dependencies: list = None,
        priority: int = 5,
    ) -> None:
        """Create a new task."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            import json

            await conn.execute(
                """
                INSERT INTO tasks (
                    id, job_id, agent_id, task_type, status,
                    priority, input_data, dependencies
                )
                VALUES ($1, $2, $3, $4, 'pending', $5, $6::jsonb, $7)
                """,
                task_id,
                job_id,
                agent_id,
                task_type,
                priority,
                json.dumps(input_data),
                dependencies or [],
            )

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        output_data: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update task status.

        Returns:
            True if a row was updated, False if the task did not exist.
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            if output_data is not None:
                import json

                res = await conn.execute(
                    """
                    UPDATE tasks
                    SET status = $2, output_data = $3::jsonb, completed_at = NOW()
                    WHERE id = $1
                    """,
                    task_id,
                    status,
                    json.dumps(output_data),
                )
            elif error:
                res = await conn.execute(
                    """
                    UPDATE tasks
                    SET status = $2, error = $3
                    WHERE id = $1
                    """,
                    task_id,
                    status,
                    error,
                )
            else:
                res = await conn.execute(
                    """
                    UPDATE tasks
                    SET status = $2
                    WHERE id = $1
                    """,
                    task_id,
                    status,
                )

            try:
                return int(res.split()[-1]) > 0
            except Exception:
                return False


# Global PostgreSQL client instance
postgres_client = PostgresClient()
