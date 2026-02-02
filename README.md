# Agent Bus

Multi-agent SWE planning system that generates comprehensive software project specifications and documentation.

---

## Documentation

| Document | Description |
|----------|-------------|
| **[User Guide](docs/USER_GUIDE.md)** | How to use Agent Bus, write requirements, understand deliverables |
| [Architecture](docs/ARCHITECTURE.md) | System design, workflow diagrams, service topology |
| [Skills System](docs/SKILLS_SYSTEM.md) | Creating and managing Claude Skills |
| [Memory Store](docs/MEMORY_STORE.md) | Pattern storage and retrieval system |
| [API Document Processing](docs/API_DOCUMENT_PROCESSING.md) | External API document ingestion |
| [Release Guide](docs/RELEASE.md) | Deployment and release process |

> **New to Agent Bus?** Start with the **[User Guide](docs/USER_GUIDE.md)**.

---

## Overview

Agent Bus orchestrates 12 specialized AI agents to generate complete software project specifications: PRD, architecture, UI/UX design, development plans, QA strategy, security review, and documentation.

> **Note**: This system generates planning documents and specifications, not runnable code. For code generation, see the companion project `agent_bus_code`.

## Why Agent Bus? (vs. Simple Prompting)

| Aspect | Simple Prompting | Agent Bus |
|--------|------------------|-----------|
| **Document Continuity** | Each document generated independently | Architecture receives the *exact* approved PRD |
| **Human Review** | Can't pause mid-workflow | HITL gates pause for human approval |
| **Learning** | Every project starts from scratch | ChromaDB stores patterns for reuse |
| **Parallelism** | Sequential only | QA, Security, Docs run concurrently |
| **Failure Recovery** | Start over on failure | Resume from exact workflow stage |
| **Audit Trail** | No record | Full event log of agent actions |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Anthropic API Key ([console.anthropic.com](https://console.anthropic.com))

### Setup

```bash
git clone https://github.com/tefj-fun/agent_bus.git
cd agent_bus
cp .env.example .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

docker compose up -d
```

### Verify

```bash
docker compose ps                    # All services should be "Up"
curl http://localhost:8000/health    # Returns {"status":"healthy"}
```

### Access

- **Web UI**: http://localhost:8000/ui/
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/api/metrics

---

## Basic Usage

### Web UI

The simplest way to use Agent Bus is through the web interface at http://localhost:8000/ui/

| Route | Description |
|-------|-------------|
| `/ui/` | Home page - create new projects |
| `/ui/jobs` | View all jobs and their status |
| `/ui/prd/{job_id}` | View PRD with approve/reject buttons |
| `/ui/plan/{job_id}` | View project plan |

### API

Alternatively, use the REST API directly:

#### Create a Project

```bash
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my-project",
    "requirements": "Build a SaaS analytics dashboard with user auth and real-time charts"
  }'
```

#### Check Status

```bash
curl http://localhost:8000/api/projects/{job_id}
```

#### Approve PRD (HITL Gate)

```bash
curl -X POST http://localhost:8000/api/projects/{job_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

For detailed API usage, event streaming, and artifact downloads, see the [User Guide](docs/USER_GUIDE.md).

---

## Project Structure

```
agent_bus/
├── src/
│   ├── agents/           # 12+ specialized agents
│   ├── orchestration/    # Master agent and workflow
│   ├── workers/          # Task execution
│   ├── infrastructure/   # Redis, PostgreSQL, LLM clients
│   ├── memory/           # ChromaDB vector store
│   ├── skills/           # Claude Skills system
│   └── api/              # FastAPI routes
├── skills/               # Local skills directory
├── tests/                # Test suites
└── docker-compose.yml
```

---

## Development

```bash
# Run tests
docker compose run --rm api pytest -q

# View logs
docker compose logs -f api worker orchestrator

# Stop services
docker compose down -v
```

See [Architecture](docs/ARCHITECTURE.md) for system design details.

---

## Configuration

Key environment variables (see `.env.example` for full list):

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key (required) |
| `REDIS_HOST` | Redis hostname |
| `POSTGRES_HOST` | PostgreSQL hostname |
| `SKILLS_DIRECTORY` | Path to skills directory |

---

## License

MIT

## Contributing

See [PLAN.md](PLAN.md) for implementation roadmap.
