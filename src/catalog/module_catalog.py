"""Module catalog store backed by PostgreSQL."""
from __future__ import annotations

import json
from typing import Any, Dict, List

import asyncpg


async def fetch_module_catalog(db_pool: asyncpg.Pool) -> Dict[str, Any]:
    """Fetch active modules from the catalog."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT module_id, name, capabilities, owner, description, version
            FROM module_catalog
            WHERE active = TRUE
            ORDER BY module_id
            """
        )

    modules = []
    for row in rows:
        modules.append(
            {
                "module_id": row["module_id"],
                "name": row["name"],
                "capabilities": row["capabilities"] or [],
                "owner": row["owner"],
                "description": row["description"],
                "version": row["version"],
            }
        )
    return {"modules": modules}


async def seed_module_catalog(
    db_pool: asyncpg.Pool, modules: List[Dict[str, Any]]
) -> int:
    """Upsert modules into the catalog. Returns number of modules processed."""
    if not modules:
        return 0

    async with db_pool.acquire() as conn:
        for module in modules:
            await conn.execute(
                """
                INSERT INTO module_catalog (module_id, name, capabilities, owner, description, version, active)
                VALUES ($1, $2, $3::jsonb, $4, $5, $6, TRUE)
                ON CONFLICT (module_id) DO UPDATE
                SET name = EXCLUDED.name,
                    capabilities = EXCLUDED.capabilities,
                    owner = EXCLUDED.owner,
                    description = EXCLUDED.description,
                    version = EXCLUDED.version,
                    active = TRUE,
                    updated_at = NOW()
                """,
                module.get("module_id"),
                module.get("name") or module.get("module_id"),
                json.dumps(module.get("capabilities") or []),
                module.get("owner"),
                module.get("description"),
                int(module.get("version") or 1),
            )
    return len(modules)


async def catalog_is_empty(db_pool: asyncpg.Pool) -> bool:
    async with db_pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM module_catalog")
    return (count or 0) == 0
