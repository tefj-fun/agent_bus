"""FastAPI application for agent_bus."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .infrastructure.container import container
from .infrastructure.redis_client import redis_client
from .infrastructure.postgres_client import postgres_client
from .api.routes import projects, memory, skills, artifacts, patterns, metrics, events, settings as settings_routes, modules
from .api.routes import ui, ui_jobs
from .api.routes import ui_prd
from .api.routes import ui_prd_actions
from .api.routes import ui_plan
from .api.routes import api_documents
from .api.error_handling import setup_error_handlers
from .config import settings
from .storage.artifact_store import init_artifact_store
from .catalog.module_catalog import catalog_is_empty, seed_module_catalog
from pathlib import Path
import json


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting agent_bus API...")

    # Initialize DI container (lazy connection initialization)
    await container.init()
    print(f"Connected to Redis at {settings.redis_host}:{settings.redis_port}")
    print(f"Connected to PostgreSQL at {settings.postgres_host}:{settings.postgres_port}")

    # Also connect legacy clients for backwards compatibility
    await redis_client.connect()
    await postgres_client.connect()

    # Initialize artifact store for file-based output storage
    if settings.artifact_storage_backend == "file":
        init_artifact_store(settings.artifact_output_dir)
        print(f"Artifact store initialized at {settings.artifact_output_dir}")

    # Seed module catalog (best effort) so feature tree has a global baseline
    if settings.module_catalog_seed_on_startup:
        try:
            pool = await postgres_client.get_pool()
            if await catalog_is_empty(pool):
                path = Path(settings.module_catalog_path)
                if path.exists():
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    modules = payload.get("modules") if isinstance(payload, dict) else None
                    if isinstance(modules, list) and modules:
                        await seed_module_catalog(pool, modules)
                        print(f"Seeded module catalog with {len(modules)} modules")
        except Exception as exc:
            print(f"Module catalog seed skipped: {exc}")

    yield

    # Shutdown
    print("Shutting down agent_bus API...")
    await container.close()
    await redis_client.close()
    await postgres_client.close()


# Create FastAPI app
# Configure servers for Swagger UI - uses relative path by default so it works on any host
app = FastAPI(
    title="Agent Bus API",
    description="Multi-agent SWE engineering system",
    version="0.1.0",
    lifespan=lifespan,
    servers=[{"url": settings.api_base_url, "description": "API Server"}],
)

# Setup standardized error handlers
setup_error_handlers(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(skills.router, prefix="/api", tags=["skills"])
app.include_router(artifacts.router, prefix="/api/artifacts", tags=["artifacts"])
app.include_router(modules.router, prefix="/api/modules", tags=["modules"])
app.include_router(ui.router, prefix="/ui", tags=["ui"])
app.include_router(ui_jobs.router, prefix="/ui", tags=["ui"])
app.include_router(ui_prd.router, prefix="/ui", tags=["ui"])
app.include_router(ui_prd_actions.router, prefix="/ui", tags=["ui"])
app.include_router(ui_plan.router, prefix="/ui", tags=["ui"])
app.include_router(api_documents.router, tags=["api-documents"])
app.include_router(patterns.router)
app.include_router(metrics.router)
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(settings_routes.router, prefix="/api", tags=["settings"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"name": "Agent Bus API", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint.

    Returns 200 when dependencies are reachable; 503 otherwise.
    """
    redis_ok = False
    pg_ok = False

    # Redis ping
    try:
        client = await redis_client.get_client()
        pong = await client.ping()
        redis_ok = bool(pong)
    except Exception:
        redis_ok = False

    # Postgres simple query
    try:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        pg_ok = True
    except Exception:
        pg_ok = False

    overall_ok = redis_ok and pg_ok

    if not overall_ok:
        # FastAPI lets you set status_code by returning a Response, but keeping it simple:
        # raise HTTPException for 503.
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "redis": "connected" if redis_ok else "down",
                "postgres": "connected" if pg_ok else "down",
            },
        )

    return {
        "status": "healthy",
        "redis": "connected",
        "postgres": "connected",
    }
