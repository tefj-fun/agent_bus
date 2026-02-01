"""FastAPI application for agent_bus."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .infrastructure.redis_client import redis_client
from .infrastructure.postgres_client import postgres_client
from .api.routes import projects, memory
from .api.routes import ui, ui_jobs
from .api.routes import ui_prd
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting agent_bus API...")
    await redis_client.connect()
    await postgres_client.connect()
    print(f"Connected to Redis at {settings.redis_host}:{settings.redis_port}")
    print(f"Connected to PostgreSQL at {settings.postgres_host}:{settings.postgres_port}")

    yield

    # Shutdown
    print("Shutting down agent_bus API...")
    await redis_client.close()
    await postgres_client.close()


# Create FastAPI app
app = FastAPI(
    title="Agent Bus API",
    description="Multi-agent SWE engineering system",
    version="0.1.0",
    lifespan=lifespan
)

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
app.include_router(ui.router, prefix="/ui", tags=["ui"])
app.include_router(ui_jobs.router, prefix="/ui", tags=["ui"])
app.include_router(ui_prd.router, prefix="/ui", tags=["ui"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Agent Bus API",
        "version": "0.1.0",
        "status": "running"
    }


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
