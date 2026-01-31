"""FastAPI application for agent_bus."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .infrastructure.redis_client import redis_client
from .infrastructure.postgres_client import postgres_client
from .api.routes import projects
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
    """Health check endpoint."""
    return {
        "status": "healthy",
        "redis": "connected",
        "postgres": "connected"
    }
