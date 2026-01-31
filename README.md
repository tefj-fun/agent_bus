# Agent Bus

Multi-agent SWE engineering system with distributed GPU compute and Claude Skills integration.

## Overview

Agent Bus is a comprehensive multi-agent system where sales inputs requirements, and 12 specialized AI agents collaborate to deliver complete software solutions. The system automatically routes ML/CV workloads to GPU nodes and maintains project memory for pattern reuse.

## Features

- **12 Specialized Agents**: PRD, Architecture, UI/UX Design, Development, QA, Security, Documentation, Support, Product Management, Project Management, Memory
- **Claude Skills Integration**: UI/UX Pro Max, Webapp Testing, TDD, Pypict, Systematic Debugging
- **Distributed Compute**: Kubernetes-based CPU/GPU worker orchestration
- **ML/CV Pipeline**: Auto-detection and GPU routing for ML workloads
- **Memory System**: Pattern recognition and template reuse with ChromaDB
- **Full Workflow**: From sales requirements to delivery

## Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Anthropic API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/tefj-fun/agent_bus.git
cd agent_bus
```

2. Create `.env` file:
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

3. Start services with Docker Compose:
```bash
docker-compose up -d
```

4. Check service health:
```bash
curl http://localhost:8000/health
```

## Architecture

```
Sales Input → PRD Generation → Architecture Design → UI/UX Design
    ↓
    → Development (with TDD)
    ↓
    → Parallel: [QA Testing + Security Review + Documentation + Support Docs]
    ↓
    → PM Review → Delivery
    ↓
Memory Agent stores patterns for future reuse
```

## Project Structure

```
agent_bus/
├── src/
│   ├── agents/           # Specialized agent implementations
│   ├── orchestration/    # Master agent and workflow
│   ├── workers/          # Worker processes
│   ├── infrastructure/   # Redis, PostgreSQL, Anthropic clients
│   ├── ml_pipeline/      # ML workload detection and routing
│   ├── skills/           # Skills manager and registry
│   └── api/              # FastAPI routes
├── skills/               # Local Claude Skills directory
├── k8s/                  # Kubernetes manifests
├── tests/                # Test suites
└── docker-compose.yml    # Local development setup
```

## API Usage

### Create a Project

```bash
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_001",
    "requirements": "Build a SaaS dashboard for analytics"
  }'
```

### Check Job Status

```bash
curl http://localhost:8000/api/projects/{job_id}
```

## Development

### Local Setup Without Docker

1. Install dependencies:
```bash
pip install -e .
```

2. Start Redis and PostgreSQL:
```bash
docker-compose up postgres redis
```

3. Run API server:
```bash
uvicorn src.main:app --reload
```

4. Run worker:
```bash
python -m src.workers.worker
```

### Running Tests

```bash
pytest tests/
```

## Claude Skills

### Installed Skills

- **UI/UX Pro Max** (`skills/ui-ux-pro-max/`) - Design system generation

Note: `skills/ui-ux-pro-max` is currently tracked as a **git submodule**. After cloning, run:
```bash
git submodule update --init --recursive
```

More skills can be added from:
  - [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills)
  - [karanb192/awesome-claude-skills](https://github.com/karanb192/awesome-claude-skills)

### Installing New Skills

```bash
cd skills
git clone https://github.com/user/skill-name skill-name
```

## Deployment

See [PLAN.md](PLAN.md) for detailed deployment instructions including:
- Kubernetes setup for distributed compute
- GPU node configuration
- Production environment setup

## Configuration

Environment variables (see `.env.example`):
- `ANTHROPIC_API_KEY` - Your Claude API key
- `REDIS_HOST/PORT` - Redis connection
- `POSTGRES_HOST/PORT` - PostgreSQL connection
- `SKILLS_DIRECTORY` - Path to skills directory
- `WORKER_TYPE` - `cpu` or `gpu`

## License

MIT

## Contributing

See [PLAN.md](PLAN.md) for implementation roadmap and contribution guidelines.
