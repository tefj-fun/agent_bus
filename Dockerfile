FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

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
    pytest-asyncio==0.21.1

# Copy application code
COPY src/ ./src/
COPY skills/ ./skills/
COPY tests/ ./tests/
COPY scripts/ ./scripts/

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
