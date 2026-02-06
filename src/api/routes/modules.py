"""API routes for module catalog management."""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

from ...config import settings
from ...infrastructure.postgres_client import postgres_client
from ...catalog.module_catalog import fetch_module_catalog, seed_module_catalog


router = APIRouter()


@router.get("/")
async def list_modules():
    """List active modules from the catalog."""
    try:
        pool = await postgres_client.get_pool()
        return await fetch_module_catalog(pool)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/seed")
async def seed_modules():
    """Seed catalog from config/platform_modules.json."""
    try:
        path = Path(settings.module_catalog_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Module catalog file not found")

        payload = json.loads(path.read_text(encoding="utf-8"))
        modules = payload.get("modules") if isinstance(payload, dict) else None
        if not isinstance(modules, list) or not modules:
            raise HTTPException(status_code=400, detail="Module catalog file is empty")

        pool = await postgres_client.get_pool()
        count = await seed_module_catalog(pool, modules)
        return {"status": "success", "seeded": count}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
