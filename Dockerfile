# Multi-stage Dockerfile for agent_bus - Production Ready
# Stage 1: Builder - Install dependencies and build
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (better layer caching)
COPY pyproject.toml ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn[standard]==0.27.0 \
    redis==5.0.0 \
    psycopg2-binary==2.9.9 \
    anthropic==0.18.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    sqlalchemy==2.0.25 \
    alembic==1.13.0 \
    asyncpg==0.29.0 \
    httpx==0.27.2 \
    python-multipart==0.0.9 \
    pytest==8.0.0 \
    pytest-asyncio==0.21.1 \
    chromadb==0.4.22 \
    sentence-transformers==2.3.1 \
    packaging==23.0 \
    pyyaml==6.0 \
    prometheus-client==0.19.0

# Stage 2: Runtime - Minimal production image
FROM python:3.11-slim AS runtime

# Create non-root user for security
RUN groupadd -r agent_bus && useradd -r -g agent_bus agent_bus

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment to use venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application code
COPY --chown=agent_bus:agent_bus src/ ./src/
COPY --chown=agent_bus:agent_bus skills/ ./skills/
COPY --chown=agent_bus:agent_bus scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p /app/logs /workspace && \
    chown -R agent_bus:agent_bus /app /workspace

# Switch to non-root user
USER agent_bus

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose or k8s)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
