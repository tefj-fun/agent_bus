# Docker Deployment Guide

## Overview

This document describes the optimized Docker setup for agent_bus, including multi-stage builds, health checks, and production best practices.

## Dockerfile Features

### Multi-Stage Build

The Dockerfile uses a two-stage build process:

1. **Builder Stage** (`builder`)
   - Installs build dependencies (gcc, g++, git)
   - Creates Python virtual environment
   - Installs all Python dependencies
   - Result: Virtual environment with all dependencies

2. **Runtime Stage** (`runtime`)
   - Uses minimal base image (python:3.11-slim)
   - Copies only the virtual environment from builder
   - No build tools included
   - Result: Small, secure production image

### Benefits

- **Smaller Image Size**: Build dependencies not included in final image
- **Faster Builds**: Dependencies layer cached separately
- **Security**: Non-root user, minimal attack surface
- **Production Ready**: Health checks, proper signal handling

### Security Features

- Non-root user (`agent_bus:agent_bus`)
- No write permissions for application code
- Minimal base image
- No unnecessary packages

## Image Size Comparison

| Version | Size | Notes |
|---------|------|-------|
| Old (single-stage) | ~1.2GB | Includes build tools |
| New (multi-stage) | ~800MB | Only runtime dependencies |

## Health Checks

All services include health checks:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1
```

## Building Images

### Development Build

```bash
docker build -t agent_bus:dev .
```

### Production Build

```bash
docker build -t agent_bus:latest --target runtime .
```

### Build Arguments

None required - all configuration via environment variables at runtime.

## Docker Compose

### Development

Use `docker-compose.yml` for local development:

```bash
docker-compose up -d
```

Features:
- Hot reload enabled
- Source code mounted as volume
- Debug mode enabled
- Local credentials

### Production

Use `docker-compose.prod.yml` for production-like deployment:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Features:
- Optimized for production
- Resource limits configured
- No source code volumes
- Health checks enabled
- Auto-restart policies
- Multiple worker replicas

## Environment Variables

Required:
- `ANTHROPIC_API_KEY` - Claude API key
- `POSTGRES_PASSWORD` - Database password (production)

Optional:
- `LLM_MODE` - `real` or `mock` (default: `real`)
- `LLM_PROVIDER` - `anthropic` or `openai` (default: `anthropic`)
- `OPENAI_API_KEY` - If using OpenAI
- `OPENAI_MODEL` - OpenAI model name

## Resource Limits

### API Service
- CPU: 1-2 cores
- Memory: 1-2GB
- Replicas: 2 (production)

### Worker Service
- CPU: 1-2 cores
- Memory: 1-2GB
- Replicas: 3 (production)

### Orchestrator
- CPU: 0.5-1 core
- Memory: 1GB
- Replicas: 1

### PostgreSQL
- CPU: 0.5-1 core
- Memory: 512MB-1GB

### Redis
- CPU: 0.5 core
- Memory: 512MB
- Max memory policy: `allkeys-lru`

## Testing

### Build Test

```bash
docker build -t agent_bus:test .
```

### Run Test Container

```bash
docker run --rm agent_bus:test python -c "import src.main; print('OK')"
```

### Health Check Test

```bash
docker-compose up -d
sleep 30
docker inspect agent_bus_api | grep -A 5 Health
```

## Production Deployment

1. Build production image:
```bash
docker build -t agent_bus:v1.0.0 --target runtime .
```

2. Tag for registry:
```bash
docker tag agent_bus:v1.0.0 your-registry.com/agent_bus:v1.0.0
docker tag agent_bus:v1.0.0 your-registry.com/agent_bus:latest
```

3. Push to registry:
```bash
docker push your-registry.com/agent_bus:v1.0.0
docker push your-registry.com/agent_bus:latest
```

4. Deploy:
```bash
# Pull on production server
docker pull your-registry.com/agent_bus:latest

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

## Monitoring

### Container Logs

```bash
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f orchestrator
```

### Container Stats

```bash
docker stats agent_bus_api agent_bus_worker agent_bus_orchestrator
```

### Health Status

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

## Troubleshooting

### Build Failures

1. Check Docker version: `docker --version` (requires 20.10+)
2. Clear build cache: `docker builder prune`
3. Build with no cache: `docker build --no-cache -t agent_bus:test .`

### Container Won't Start

1. Check logs: `docker logs agent_bus_api`
2. Verify environment variables: `docker exec agent_bus_api env | grep -E '(ANTHROPIC|POSTGRES|REDIS)'`
3. Check health: `docker inspect agent_bus_api | grep Health -A 10`

### Permission Issues

Container runs as non-root user `agent_bus`. Ensure volumes have correct permissions:

```bash
sudo chown -R 1000:1000 /path/to/volumes
```

## Best Practices

1. **Use .dockerignore** - Exclude unnecessary files from build context
2. **Pin Dependencies** - Use exact versions in pyproject.toml
3. **Layer Caching** - Copy dependencies before application code
4. **Health Checks** - Always include health checks in production
5. **Resource Limits** - Set CPU/memory limits to prevent resource exhaustion
6. **Non-Root User** - Never run containers as root
7. **Secrets** - Use environment variables or secrets management, never hardcode

## Next Steps

See [K8S.md](./K8S.md) for Kubernetes deployment guide.
