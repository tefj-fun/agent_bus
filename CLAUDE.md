# CLAUDE.md - AI Assistant Guide for Agent Bus

This document provides essential information for AI assistants working with the Agent Bus codebase.

## Project Overview

**Agent Bus** is a multi-agent SWE (Software Engineering) planning system where 12+ specialized AI agents collaborate to generate comprehensive software project specifications and documentation. The system processes requirements through a complete workflow: PRD generation → Architecture → UI/UX Design → Development Planning → QA Strategy → Security Review → Documentation → Support Docs → PM Review → Delivery.

> **Note**: This system generates planning documents and specifications (PRDs, architecture designs, development plans, etc.), not actual runnable code. For code generation based on these specifications, see the companion project `agent_bus_code`.

### Key Features

- 12+ specialized agents coordinated by a master orchestrator
- Redis-based async task queue for job processing
- PostgreSQL for state persistence and artifact storage
- ChromaDB vector database for semantic memory and pattern recognition
- Claude Skills integration for extensible capabilities
- Human-in-the-loop (HITL) approval gates
- Real-time event streaming (SSE)
- Prometheus metrics and structured JSON logging

## Repository Structure

```
agent_bus/
├── src/                          # Main application code
│   ├── agents/                   # 15 specialized agents
│   │   ├── base.py              # BaseAgent abstract class (AgentContext, AgentTask, AgentResult)
│   │   ├── prd_agent.py         # Product Requirements Document generation
│   │   ├── architect_agent.py   # System architecture design
│   │   ├── uiux_agent.py        # UI/UX design system generation
│   │   ├── developer_agent.py   # Code generation with TDD
│   │   ├── qa_agent.py          # Test planning and QA strategy
│   │   ├── security_agent.py    # Security review and vulnerability detection
│   │   ├── technical_writer.py  # Documentation generation
│   │   ├── support_engineer.py  # Support documentation
│   │   ├── product_manager.py   # Product decisions
│   │   ├── project_manager.py   # Project management
│   │   ├── plan_agent.py        # Milestone and task planning
│   │   ├── memory_agent.py      # Legacy pattern storage
│   │   ├── memory_agent_v2.py   # Enhanced pattern management
│   │   ├── delivery_agent.py    # Final delivery coordination
│   │   └── api_document_agent.py # External API document processing
│   │
│   ├── orchestration/            # Workflow management
│   │   ├── master_agent.py      # Main orchestrator - coordinates all agents
│   │   ├── orchestrator.py      # Orchestrator runner process
│   │   └── workflow.py          # WorkflowStateMachine with 13+ stages
│   │
│   ├── api/                      # FastAPI REST endpoints
│   │   ├── main.py              # FastAPI app setup with lifespan management
│   │   └── routes/              # Route handlers (projects, memory, patterns, skills, events, metrics)
│   │
│   ├── infrastructure/           # Core services
│   │   ├── redis_client.py      # Async Redis connection management
│   │   ├── postgres_client.py   # Async PostgreSQL connection pooling
│   │   ├── anthropic_client.py  # Anthropic Claude LLM client wrapper
│   │   └── openai_client.py     # OpenAI LLM client wrapper
│   │
│   ├── memory/                   # Memory system v2 (ChromaDB-based)
│   │   ├── chroma_store.py      # ChromaDB vector store implementation
│   │   ├── postgres_store.py    # PostgreSQL metadata store
│   │   ├── embedding_generator.py # Sentence-transformer embeddings
│   │   └── retention.py         # Pattern retention policies
│   │
│   ├── api_docs/                 # External API document processing
│   │   ├── schema.py            # Pydantic models for API documents
│   │   ├── parser.py            # Multi-format document parser
│   │   └── policy_extractor.py  # LLM-based policy extraction
│   │
│   ├── skills/                   # Claude Skills system
│   │   ├── schema.py            # Pydantic models for skill.json validation
│   │   ├── registry.py          # Automatic skill discovery and validation
│   │   ├── manager.py           # Skill loading, caching, git installation
│   │   └── allowlist.py         # Skill capability allowlisting
│   │
│   ├── workers/                 # Task execution
│   │   └── worker.py            # Worker process for agent task execution
│   │
│   ├── config.py                # Pydantic Settings for environment configuration
│   ├── cli.py                   # Skills CLI (agent-bus-skills command)
│   ├── cli_memory.py            # Memory CLI (agent-bus-memory command)
│   └── cli_jobs.py              # Jobs CLI (agent-bus-jobs command)
│
├── skills/                       # Local Claude Skills directory
│   └── weather-toolkit/         # Reference implementation example
│
├── web/                          # React frontend (Vite + TypeScript + TailwindCSS)
│   ├── src/
│   │   ├── api/                 # API client with typed fetch wrapper
│   │   ├── components/          # UI, domain, and layout components
│   │   ├── hooks/               # React Query hooks (useProject, useMemory, useEventStream)
│   │   ├── pages/               # Route pages (Dashboard, CreateProject, PRDReview, etc.)
│   │   ├── styles/              # TailwindCSS design tokens
│   │   ├── types/               # TypeScript definitions
│   │   └── utils/               # Utility functions
│   ├── package.json
│   └── vite.config.ts
│
├── tests/                        # Comprehensive test suite (30+ test files)
├── scripts/                     # Automation scripts
├── docs/                        # Documentation
├── docker-compose.yml           # Local development setup
└── pyproject.toml               # Poetry package configuration
```

## Tech Stack

### Backend

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.10+ |
| Web Framework | FastAPI | ^0.109.0 |
| Task Queue | Redis | ^5.0.0 |
| Database | PostgreSQL (asyncpg) | ^0.29.0 |
| Vector Store | ChromaDB | ^0.4.22 |
| Embeddings | sentence-transformers | ^2.3.1 |
| LLM Client | anthropic | ^0.18.0 |
| ORM | SQLAlchemy | ^2.0.25 |
| Migrations | Alembic | ^1.13.0 |
| Metrics | prometheus-client | ^0.19.0 |
| Container | Docker + docker-compose V2 |

### Frontend (web/)

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | React | ^18.x |
| Language | TypeScript | ^5.x |
| Build Tool | Vite | ^7.x |
| Styling | TailwindCSS | ^4.x |
| State | TanStack Query | ^5.x |
| Routing | React Router | ^6.x |
| Icons | Lucide React | ^0.x |

### UI Design System

**IMPORTANT**: All UI components must follow the design system defined in `docs/UIUX_PLAN.md` and use the tokens from `web/src/styles/tokens.css`.

#### Design Tokens Location

| File | Purpose |
|------|---------|
| `web/src/styles/tokens.css` | CSS custom properties for colors, typography, animations |
| `docs/UIUX_PLAN.md` | Complete design system specification |

#### Color Palette

```css
/* Brand - Primary Blue */
--color-primary-500: #3b82f6;    /* Main actions, links */
--color-primary-600: #2563eb;    /* Hover states */
--color-primary-700: #1d4ed8;    /* Active states */

/* Semantic Colors */
--color-success-500: #22c55e;    /* Completed, approved */
--color-warning-500: #f59e0b;    /* Pending review, caution */
--color-error-500: #ef4444;      /* Failed, rejected */

/* Workflow Stage Colors (each agent has a distinct color) */
--color-stage-prd: #8b5cf6;      /* Purple - PRD */
--color-stage-plan: #ec4899;     /* Pink - Planning */
--color-stage-arch: #f97316;     /* Orange - Architecture */
--color-stage-uiux: #14b8a6;     /* Teal - UI/UX */
--color-stage-dev: #3b82f6;      /* Blue - Development */
--color-stage-qa: #22c55e;       /* Green - QA */
--color-stage-security: #ef4444; /* Red - Security */
--color-stage-docs: #6366f1;     /* Indigo - Documentation */
```

#### UI Component Guidelines

1. **Use Tailwind utilities** with the custom color tokens (e.g., `bg-primary-500`, `text-error-600`)
2. **Base components** are in `web/src/components/ui/` (Button, Card, Badge, etc.)
3. **Domain components** are in `web/src/components/domain/` (WorkflowProgress, ActivityFeed, etc.)
4. **Always use semantic colors** for status indicators:
   - Success states: `success-*` colors (green)
   - Warning/pending: `warning-*` colors (amber)
   - Error/failed: `error-*` colors (red)
   - Info/active: `primary-*` colors (blue)

#### Typography

```css
--font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
--font-mono: 'JetBrains Mono', ui-monospace, monospace;
```

#### Animation Tokens

```css
--duration-fast: 150ms;    /* Hover effects, small transitions */
--duration-normal: 250ms;  /* Modal/toast animations */
--duration-slow: 400ms;    /* Page transitions */
```

## Development Commands

### Quick Start

```bash
# Clone and configure
git clone https://github.com/tefj-fun/agent_bus.git
cd agent_bus
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY

# Start all services
docker compose up -d

# Verify
curl http://localhost:8000/health
```

### Running Services

```bash
# Start all services (API, Worker, Orchestrator, Redis, PostgreSQL)
docker compose up -d

# View logs
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f orchestrator

# Stop services
docker compose down -v
```

### Testing

```bash
# Run all tests (in Docker)
docker compose run --rm api pytest -q

# Run tests excluding slow ones
docker compose run --rm api pytest -q -m "not slow"

# Run specific test file
docker compose run --rm api pytest tests/test_skills_manager.py -v

# Run locally (requires services running)
pytest tests/
```

### Memory System

```bash
# Seed templates
python scripts/seed_templates.py

# Run smoke test
./scripts/memory_smoke.sh

# CLI commands
agent-bus-memory query "search term" --top-k 5
agent-bus-memory list
agent-bus-memory health
```

### Skills Management

```bash
# CLI commands
agent-bus-skills list
agent-bus-skills info <skill-name>
agent-bus-skills install <github-url> --name <skill-name>
agent-bus-skills update <skill-name>
```

### Job Management (CLI)

```bash
# CLI commands
agent-bus-jobs list                     # List all jobs
agent-bus-jobs status <job_id>          # Show detailed job status
agent-bus-jobs watch <job_id>           # Watch job progress in real-time
agent-bus-jobs result <job_id>          # View all job artifacts
agent-bus-jobs result <job_id> -a prd   # View specific artifact (prd, plan, architecture, etc.)
agent-bus-jobs approve <job_id>         # Approve PRD to continue workflow
```

### Web UI Development

```bash
# Navigate to web directory
cd web

# Install dependencies
npm install

# Start development server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run build  # runs tsc -b first
```

### Release Process

```bash
# Bump version and create release
./scripts/release.sh patch   # or minor/major

# This automatically:
# - Bumps version in pyproject.toml
# - Updates CHANGELOG.md
# - Creates git tag
# - Triggers CI/CD pipeline
```

## Code Conventions

### Python Style

- **Python version**: 3.10+ (async/await patterns throughout)
- **Formatter**: Black with 100-character line length
- **Linter**: Ruff
- **Type checker**: mypy with strict settings (`disallow_untyped_defs = true`)
- **All I/O is async**: Use `async def` for database, Redis, and LLM calls

### Type Hints (Mandatory)

```python
from typing import Dict, List, Optional, Any

async def execute(self, task: AgentTask) -> AgentResult:
    ...
```

### Data Models (Pydantic v2)

```python
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    project_id: str
    requirements: str
    metadata: Optional[Dict[str, Any]] = None
```

### Agent Pattern

All agents inherit from `BaseAgent` and implement three required methods:

```python
class MyAgent(BaseAgent):
    def get_agent_id(self) -> str:
        return "my_agent"

    def define_capabilities(self) -> Dict[str, Any]:
        return {"type": "specialized", "domain": "..."}

    async def execute(self, task: AgentTask) -> AgentResult:
        # Implementation
        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            success=True,
            output={"result": "..."},
            artifacts=[]
        )
```

### LLM Calls

Use `query_llm()` method from `BaseAgent`:

```python
response = await self.query_llm(
    prompt="Your prompt here",
    system="System instructions",
    model=None,  # Uses default from config
    thinking_budget=1024,
    max_tokens=8192,
)
```

### Artifacts

Save outputs using `save_artifact()`:

```python
artifact_id = await self.save_artifact(
    artifact_type="prd",  # prd, code, test, documentation, etc.
    content="Content here",
    metadata={"version": "1.0"}
)
```

### Testing Pattern

```python
import pytest

@pytest.mark.asyncio
async def test_agent_execution():
    context = create_test_context()
    agent = MyAgent(context)
    result = await agent.execute(test_task)
    assert result.success
```

## Environment Variables

Key environment variables (see `.env.example` for full list):

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude API key (required for real mode) | - |
| `ANTHROPIC_MODEL` | Model to use | `claude-sonnet-4-5-20250929` |
| `LLM_MODE` | `real` or `mock` (for testing) | `real` |
| `LLM_PROVIDER` | `anthropic` or `openai` | `anthropic` |
| `REDIS_HOST` | Redis hostname | `localhost` |
| `POSTGRES_HOST` | PostgreSQL hostname | `localhost` |
| `POSTGRES_PASSWORD` | PostgreSQL password | (required) |
| `CHROMA_PERSIST_DIRECTORY` | ChromaDB data path | `./data/chroma` |
| `SKILLS_DIRECTORY` | Skills directory path | `./skills` |

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/projects/` | List all jobs |
| `POST` | `/api/projects/` | Create new project |
| `GET` | `/api/projects/{job_id}` | Get job status |
| `DELETE` | `/api/projects/{job_id}` | Delete a job |
| `GET` | `/api/projects/{job_id}/prd` | Get PRD artifact |
| `GET` | `/api/projects/{job_id}/plan` | Get project plan artifact |
| `GET` | `/api/projects/{job_id}/architecture` | Get architecture artifact |
| `GET` | `/api/projects/{job_id}/export` | Export all artifacts as ZIP |
| `GET` | `/api/projects/{job_id}/memory_hits` | Get memory pattern hits from PRD generation |
| `POST` | `/api/projects/{job_id}/approve` | Approve PRD (HITL) |
| `POST` | `/api/projects/{job_id}/request_changes` | Request changes to PRD |
| `POST` | `/api/projects/{job_id}/restart` | Restart a failed job |
| `POST` | `/api/patterns/store` | Store a pattern |
| `POST` | `/api/patterns/query` | Search patterns |
| `POST` | `/api/patterns/suggest` | Get template suggestions |
| `GET` | `/api/events/stream` | SSE event stream |
| `GET` | `/api/events/history` | Get event history |
| `GET` | `/api/metrics` | Prometheus metrics |

### API Document Processing Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/api-documents/process` | Process and store an API document |
| `POST` | `/api/api-documents/upload` | Upload API document file |
| `POST` | `/api/api-documents/query/endpoints` | Search for relevant endpoints |
| `POST` | `/api/api-documents/query/policies` | Get policies for an API |
| `POST` | `/api/api-documents/suggest/integration` | Get integration suggestions |
| `POST` | `/api/api-documents/context/development` | Get dev context for a task |
| `GET` | `/api/api-documents/list` | List all stored API documents |
| `GET` | `/api/api-documents/{doc_id}` | Get specific API document |
| `DELETE` | `/api/api-documents/{doc_id}` | Delete an API document |

### Web UI (Legacy Server-Rendered)

Minimal server-rendered HTML interface:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/ui/` | Home page - project creation form |
| `POST` | `/ui/create` | Submit new project |
| `GET` | `/ui/jobs` | List all jobs |
| `GET` | `/ui/prd/{job_id}` | View PRD with approve/reject buttons |
| `POST` | `/ui/prd/{job_id}/approve` | Approve PRD |
| `POST` | `/ui/prd/{job_id}/request_changes` | Request changes to PRD |
| `GET` | `/ui/plan/{job_id}` | View project plan |

### Web UI (React Frontend)

Modern React-based interface at `http://localhost:3000/`:

| Route | Description |
|-------|-------------|
| `/` | Dashboard - stats, pending reviews, project lists |
| `/new` | Create project with memory-assisted suggestions |
| `/project/:jobId` | Workflow progress with real-time SSE updates |
| `/prd/:jobId` | PRD review with approve/request changes (HITL gate) |
| `/project/:jobId/deliverables` | Download generated artifacts |
| `/memory` | Search and browse stored patterns |

See `web/README.md` for setup instructions.

### API Documentation

- React Web UI: `http://localhost:3000/` (requires `cd web && npm run dev`)
- Legacy Web UI: `http://localhost:8000/ui/`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Workflow Stages

The system processes jobs through these stages:

1. **Queued** - Job received
2. **PRD_Generation** - PRD Agent creates requirements document
3. **Waiting_Approval** - HITL gate for PRD approval
4. **Plan_Generation** - Plan Agent creates milestones/tasks
5. **Architecture** - Architect Agent designs system
6. **UI_UX_Design** - UI/UX Agent creates design system
7. **Development** - Developer Agent creates development plan with TDD strategy
8. **QA_Testing** - QA Agent creates test plans (parallel)
9. **Security_Review** - Security Agent reviews vulnerabilities (parallel)
10. **Documentation** - Tech Writer creates docs (parallel)
11. **Support_Docs** - Support Engineer creates FAQ (parallel)
12. **PM_Review** - Product Manager final review
13. **Delivery** - Package artifacts

## Key Files to Understand

| File | Purpose |
|------|---------|
| `src/agents/base.py` | Abstract base class for all agents |
| `src/orchestration/master_agent.py` | Main workflow coordinator |
| `src/orchestration/workflow.py` | State machine for workflow stages |
| `src/api/routes/projects.py` | Project CRUD and status endpoints |
| `src/memory/chroma_store.py` | Vector store for pattern memory |
| `src/skills/registry.py` | Skill auto-discovery and validation |
| `src/config.py` | Environment configuration |
| `src/workers/worker.py` | Task execution engine |
| `src/api_docs/parser.py` | Multi-format API document parser |
| `src/agents/api_document_agent.py` | API document processing agent |

## Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| README | `README.md` | Quick start and overview |
| Architecture | `docs/ARCHITECTURE.md` | Service split details |
| UI/UX Plan | `docs/UIUX_PLAN.md` | Design system and component specs |
| Web UI | `web/README.md` | React frontend setup and development |
| Skills System | `docs/SKILLS_SYSTEM.md` | Skill implementation guide |
| Memory Store | `docs/MEMORY_STORE.md` | Memory system architecture |
| API Doc Processing | `docs/API_DOCUMENT_PROCESSING.md` | External API document ingestion |
| Release | `docs/RELEASE.md` | Release process |
| Implementation Plan | `PLAN.md` | Detailed roadmap |

## CI/CD Pipeline

The CI pipeline (`.github/workflows/ci.yml`) runs on every push/PR:

1. Build Docker images with layer caching
2. Start all services (API, Worker, Orchestrator, Redis, PostgreSQL)
3. Wait for API health check
4. Run pytest with `LLM_MODE=mock` (no API calls)
5. Teardown

Additional workflows:
- `release.yml` - Docker push and GitHub release on version tags
- `smoke-test.yml` - Quick validation tests
- `nightly-real-smoke.yml` - Real LLM integration tests

## Common Tasks

### Adding a New Agent

1. Create `src/agents/my_agent.py`
2. Inherit from `BaseAgent`
3. Implement `get_agent_id()`, `define_capabilities()`, `execute()`
4. Register in `src/orchestration/master_agent.py`
5. Add tests in `tests/test_my_agent.py`

### Adding a New API Endpoint

1. Create route in `src/api/routes/`
2. Add router to `src/api/main.py`
3. Add tests

### Adding a New Skill

1. Create directory in `skills/`
2. Add `skill.json` with metadata
3. Add `skill.md` with prompt content
4. Test with `pytest tests/test_example_skill_integration.py`

### Debugging

```bash
# View all service logs
docker compose logs -f

# Check specific service
docker compose logs -f api

# Interactive shell
docker compose exec api bash

# Database access
docker compose exec postgres psql -U agent_bus
```

## Important Patterns

### Error Handling

Agents should return `AgentResult` with `success=False` and an `error` message rather than raising exceptions:

```python
return AgentResult(
    task_id=task.task_id,
    agent_id=self.agent_id,
    success=False,
    output={},
    artifacts=[],
    error="Descriptive error message"
)
```

### Async Context

Always use `async with` for database connections:

```python
async with self.context.db_pool.acquire() as conn:
    await conn.execute(...)
```

### Skills Permission

Skills are loaded with permission enforcement by default:

```python
skill = await self.load_skill("skill-name", enforce_permissions=True)
```

## Database Schema

Key tables in PostgreSQL:

- `jobs` - Project jobs and workflow stages
- `tasks` - Individual agent task executions
- `artifacts` - Generated outputs (PRD, code, docs)
- `agent_events` - Event log for debugging
- `memory_patterns` - Stored patterns and templates

Initialize with: `scripts/init_db.sql`

## Troubleshooting

### Services Not Starting

```bash
docker compose ps          # Check status
docker compose logs api    # Check logs
docker compose down -v     # Clean restart
docker compose up -d
```

### Tests Failing

```bash
# Ensure LLM_MODE is set
export LLM_MODE=mock
docker compose run --rm api pytest -v
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Reset database
docker compose down -v
docker compose up -d postgres
```
