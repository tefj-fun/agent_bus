FROM python:3.11-slim AS builder

ARG WITH_PDF=0
ARG WITH_MERMAID=0

WORKDIR /app

# Build deps (only in builder)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optional PDF/diagram system deps for export tooling
RUN if [ "$WITH_PDF" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends \
        pandoc \
        libcairo2 \
        libgdk-pixbuf-xlib-2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        fonts-dejavu \
        fonts-liberation \
        fonts-noto-core \
        && rm -rf /var/lib/apt/lists/*; \
    fi

# Optional Mermaid CLI (used only by PDF export script)
RUN if [ "$WITH_MERMAID" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends nodejs npm \
        && npm install -g @mermaid-js/mermaid-cli \
        && rm -rf /var/lib/apt/lists/*; \
    fi

# Copy dependency files first (invalidate cache only when deps change)
COPY pyproject.toml ./

# Build wheels for runtime deps
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels \
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
    "numpy<2.0" \
    chromadb==0.4.22 \
    posthog==2.4.0 \
    sentence-transformers==2.3.1 \
    packaging==23.0 \
    pyyaml==6.0 \
    psutil==5.9.8

RUN if [ "$WITH_PDF" = "1" ]; then \
      pip wheel --no-cache-dir --wheel-dir /wheels weasyprint==68.0; \
    fi

FROM python:3.11-slim

ARG WITH_PDF=0
ARG WITH_MERMAID=0

WORKDIR /app

# Runtime system deps for PDF rendering only
RUN if [ "$WITH_PDF" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends \
        pandoc \
        libcairo2 \
        libgdk-pixbuf-xlib-2.0-0 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        fonts-dejavu \
        fonts-liberation \
        fonts-noto-core \
        && rm -rf /var/lib/apt/lists/*; \
    fi

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

RUN if [ "$WITH_MERMAID" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends nodejs npm \
        && npm install -g @mermaid-js/mermaid-cli \
        && rm -rf /var/lib/apt/lists/*; \
    fi

# Copy application code last (invalidates only when source changes)
COPY src/ ./src/
COPY skills/ ./skills/
COPY tests/ ./tests/
COPY scripts/ ./scripts/

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
