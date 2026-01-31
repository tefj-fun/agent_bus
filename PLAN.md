# Multi-Agent SWE Engineering System - Implementation Plan

## Overview
Build a comprehensive multi-agent system in the **agent_bus** repository (https://github.com/tefj-fun/agent_bus) where sales inputs requirements, and 12 specialized AI agents collaborate to deliver complete software solutions. The system automatically routes ML/CV workloads to GPU nodes and maintains project memory for pattern reuse.

**Repository**: `agent_bus`
**Location**: `/home/bot/clawd/agent_bus/`

## Phase 4 Status (Current)
- Async project creation returns queued job IDs; background orchestration runs in-process.
- Job status endpoint includes workflow stage, timestamps, metadata, and latest task snapshot.
- PRD retrieval endpoint prefers `artifacts` (type `prd`) with task-output fallback.
- PRD generation captures memory hits; API exposes hits per job.
- HITL gate pauses after PRD (`waiting_for_approval`) with approve/request_changes endpoints.
- PlanAgent generates milestone/task/dependency plans and stores `plan` artifacts.

## Phase 5 Status (Next)
**Goal:** Integration & end-to-end testing (CPU-only for now; ignore Jetson/GPU).
- Add a repeatable Phase 4 smoke run (script + recorded results)
- Add integration tests for the async + HITL flow (create → PRD → approve → plan)
- Stabilize orchestration so jobs can complete reliably even if the API process reloads/restarts

## System Architecture

### Core Components
1. **Web UI** (FastAPI + React) - Sales input interface
2. **Master Agent** - SWE Engineering Manager orchestrating workflow
3. **11 Specialized Agents** - Each with domain expertise
4. **Message Queue** - Redis for agent coordination
5. **State Store** - PostgreSQL for persistence
6. **Memory System** - ChromaDB vector DB for patterns/templates
7. **Distributed Compute** - Kubernetes for CPU/GPU workers
8. **LLM Backend** - Anthropic Claude for all agents

### Agent Types (Enhanced with Claude Skills)
1. **PRD Agent** - Creates Product Requirements Documents
2. **Solution Architect** - Designs system architecture
3. **UI/UX Designer Agent** ⭐ NEW - Uses **UI/UX Pro Max skill** for design system generation (67 UI styles, 96 color palettes, industry-specific reasoning)
4. **Developer Agent** - Writes code with **TDD skill** support
5. **QA Engineer** - Testing and debugging using **Webapp Testing skill** (Playwright), **Pypict skill** (pairwise test design), **Systematic Debugging skill**
6. **Security Engineer** - Security review and implementation
7. **Technical Writer** - Manual tutorials
8. **Support Engineer** - Support documentation
9. **Product Manager** - Product decisions
10. **Project Manager** - Progress/timeline tracking
11. **Memory Agent** - Pattern recognition and template suggestion
12. **SWE Engineering Manager** - Master control and orchestration

### Workflow
```
Sales Input → PRD Generation → HITL Approval → Plan Generation
    ↓
    → Architecture Design → UI/UX Design (UI/UX Pro Max)
    ↓
    → Development (with TDD)
    ↓
    → Parallel: [QA Testing (Playwright/Pypict) + Security Review + Documentation + Support Docs]
    ↓
    → PM Review → Delivery
    ↓
Memory Agent stores patterns for future reuse
```

### ML/CV Pipeline
- **Auto-detection**: System detects ML/CV workloads from requirements
- **GPU routing**: ML tasks automatically routed to Kubernetes GPU pods
- **Resource allocation**: Dynamic GPU node selection (V100/A100)
- **Fallback**: CPU nodes for non-ML workloads

## Technology Stack

### Backend
- Python 3.11+ (async/await)
- FastAPI (API & Web UI)
- Redis 7.x (task queue)
- PostgreSQL 15 (state persistence)
- Anthropic Claude SDK (LLM)

### Infrastructure
- Kubernetes 1.28+ (orchestration)
- Docker (containerization)
- Helm 3 (deployment)

### ML/AI
- ChromaDB (vector database)
- Sentence-Transformers (embeddings)
- PyTorch 2.x (ML workloads)
- CUDA 12.x (GPU support)

### Frontend
- React 18 + TypeScript
- TailwindCSS
- React Query
- WebSocket (real-time updates)

### Claude Skills & MCP
- **UI/UX Pro Max** - Design system generation with 67 UI styles, 96 color palettes, industry-specific reasoning
- **Webapp Testing** - Playwright-based testing for web apps
- **TDD Skill** - Test-driven development guidance
- **Pypict Skill** - Combinatorial test case design
- **Systematic Debugging** - Root cause analysis and debugging
- **MCP Servers** - Custom integrations for external tools/APIs

## Skills Integration Strategy

### What are Claude Skills?
Claude Skills are packaged, reusable bundles of instructions, templates, scripts, and resources that teach Claude how to perform specialized tasks. They can be loaded dynamically by agents when needed.

### Key Skills for the System

#### 1. UI/UX Pro Max Skill
**Agent**: UI/UX Designer Agent
**Source**: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
**Capabilities**:
- Auto-generates complete design systems with industry-specific reasoning
- 67 UI styles (minimalism, glassmorphism, brutalism, cyberpunk, etc.)
- 96 color palettes tailored to industries (SaaS, fintech, healthcare, etc.)
- 57 font pairings with Google Fonts integration
- 25 chart types for dashboards
- 100 industry-specific reasoning rules
- Master + Overrides pattern for persistent design systems

**Usage**:
```python
# UI/UX Designer Agent loads this skill
design_system = await self.load_skill("ui-ux-pro-max")
result = await design_system.generate({
    "industry": "fintech",
    "style": "modern minimalist",
    "components": ["landing page", "dashboard", "forms"]
})
```

#### 2. Webapp Testing Skill
**Agent**: QA Engineer Agent
**Capabilities**:
- Playwright-based automated testing
- Screenshot capture and visual regression
- Debugging UI behavior
- Handles Jest, Vitest, Playwright, Cypress, Puppeteer
- Autonomous test execution and fixing

**Usage**:
```python
# QA Engineer Agent
test_skill = await self.load_skill("webapp-testing")
results = await test_skill.test({
    "url": "http://localhost:3000",
    "flows": ["login", "checkout", "dashboard"]
})
```

#### 3. TDD Skill
**Agent**: Developer Agent
**Capabilities**:
- RED-GREEN-REFACTOR workflow
- Test-first development guidance
- Coverage analysis

#### 4. Pypict Skill
**Agent**: QA Engineer Agent
**Capabilities**:
- Pairwise Independent Combinatorial Testing (PICT)
- Optimized test suite generation
- Comprehensive test case design

#### 5. Systematic Debugging Skill
**Agent**: QA Engineer Agent, Developer Agent
**Capabilities**:
- Root cause analysis
- Hypothesis formation
- Fix application and documentation

### Skills Management Architecture

```python
# src/skills/manager.py

class SkillsManager:
    """Manages loading and execution of Claude Skills"""

    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = skills_dir
        self.loaded_skills = {}
        self.registry = SkillRegistry()

    async def load_skill(self, skill_name: str) -> Skill:
        """Load a skill from local directory"""
        if skill_name in self.loaded_skills:
            return self.loaded_skills[skill_name]

        skill_path = os.path.join(self.skills_dir, skill_name)
        skill = await self._parse_skill(skill_path)
        self.loaded_skills[skill_name] = skill
        return skill

    async def install_skill(self, git_url: str, skill_name: str):
        """Clone skill from GitHub to local directory"""
        target_path = os.path.join(self.skills_dir, skill_name)
        subprocess.run(["git", "clone", git_url, target_path])
        await self._register_skill(skill_name)
```

### Installation Process

**Phase 1 Setup**:
```bash
# Create skills directory
mkdir -p skills

# Install UI/UX Pro Max
cd skills
git clone https://github.com/nextlevelbuilder/ui-ux-pro-max-skill ui-ux-pro-max

# Search and install other skills from awesome-claude-skills
# https://github.com/ComposioHQ/awesome-claude-skills
# https://github.com/karanb192/awesome-claude-skills
```

### Skills Discovery
Use these resources to find additional skills:
- [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills)
- [karanb192/awesome-claude-skills](https://github.com/karanb192/awesome-claude-skills)
- [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)
- [Anthropic Official Skills](https://github.com/anthropics/skills)

### MCP Integration
Model Context Protocol (MCP) servers can be integrated for:
- External API connections (GitHub, Jira, Slack)
- Database access
- File system operations
- Custom tool integrations

**MCP UI Framework (2026)**: Skills can now trigger rich UI components provided by MCP servers, enabling interactive workflows.

## Directory Structure
```
agent_bus/
├── src/
│   ├── agents/
│   │   ├── base.py                    # BaseAgent class
│   │   ├── prd_agent.py
│   │   ├── solution_architect.py
│   │   ├── developer_agent.py
│   │   ├── qa_engineer.py
│   │   ├── security_engineer.py
│   │   ├── tech_writer.py
│   │   ├── support_engineer.py
│   │   ├── product_manager.py
│   │   ├── project_manager.py
│   │   ├── memory_agent.py
│   │   └── uiux_designer.py          # NEW: UI/UX design agent
│   ├── orchestration/
│   │   ├── master_agent.py           # Master control
│   │   ├── workflow.py               # State machine
│   │   └── task_router.py
│   ├── workers/
│   │   ├── worker.py                 # Worker process
│   │   └── gpu_detector.py
│   ├── infrastructure/
│   │   ├── redis_client.py
│   │   ├── postgres_client.py
│   │   ├── k8s_manager.py
│   │   └── anthropic_client.py
│   ├── ml_pipeline/
│   │   ├── detector.py               # ML workload detection
│   │   └── executor.py               # GPU job execution
│   ├── skills/
│   │   ├── manager.py                # Skills loader & manager
│   │   └── registry.py               # Skills registry
│   └── api/
│       └── routes/
│           ├── projects.py
│           └── jobs.py
├── skills/                            # LOCAL SKILLS DIRECTORY
│   ├── ui-ux-pro-max/                # UI/UX design system skill
│   ├── webapp-testing/               # Playwright testing skill
│   ├── tdd/                          # Test-driven development
│   ├── pypict/                       # Pairwise testing
│   └── systematic-debugging/         # Debugging skill
├── k8s/
│   ├── workers/
│   │   ├── cpu-deployment.yaml
│   │   └── gpu-job.yaml
│   └── monitoring/
├── web/
│   └── src/
│       └── components/
│           ├── RequirementsForm.tsx
│           └── ProjectDashboard.tsx
└── tests/
```

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Set up core infrastructure and base classes

Tasks:
- Create project structure
- **Install Claude Skills locally** (UI/UX Pro Max, Webapp Testing, TDD, Pypict, Systematic Debugging)
- Implement `SkillsManager` for loading and managing skills
- Implement `BaseAgent` class with Claude integration and skills support
- Set up Redis + PostgreSQL + Docker Compose
- Build FastAPI application skeleton
- Create basic Web UI for requirements input
- Implement `MasterAgent` orchestration skeleton

**Critical Files**:
- `src/agents/base.py`
- `src/skills/manager.py` ⭐ NEW
- `src/skills/registry.py` ⭐ NEW
- `src/orchestration/master_agent.py`
- `src/main.py`
- `docker-compose.yml`

**Skills Installation**:
```bash
mkdir -p skills
cd skills
git clone https://github.com/nextlevelbuilder/ui-ux-pro-max-skill ui-ux-pro-max
# Additional skills from awesome-claude-skills repos
```

### Phase 2: Core Agents (Weeks 3-5)
**Goal**: Implement all 12 specialized agents (including UI/UX Designer)

Tasks:
- Implement each agent extending `BaseAgent`
- **Implement UI/UX Designer Agent with UI/UX Pro Max skill integration** ⭐ NEW
- **Enhance QA Engineer with Webapp Testing, Pypict, and Systematic Debugging skills** ⭐ NEW
- **Enhance Developer Agent with TDD skill** ⭐ NEW
- Define agent capabilities and prompts
- Build Redis task queue system
- Implement workflow state machine (add UI/UX design stage)
- Add PostgreSQL artifact storage
- Create agent communication protocol

**Critical Files**:
- `src/agents/*.py` (all 12 agents including uiux_designer.py) ⭐
- `src/orchestration/workflow.py`
- `src/workers/worker.py`

### Phase 3: Memory System (Week 6)
**Goal**: Enable pattern recognition and reuse

Tasks:
- Integrate ChromaDB
- Implement `MemoryAgent` with vector search
- Build pattern storage and retrieval
- Add template suggestion system
- Seed initial templates

**Critical Files**:
- `src/agents/memory_agent.py`
- `src/memory/vector_store.py`

### Phase 4: Kubernetes Integration (Weeks 7-8)
**Goal**: Set up distributed compute infrastructure

Tasks:
- Create Docker images for workers
- Write Kubernetes manifests (CPU + GPU)
- Implement `KubernetesJobManager`
- Set up CPU worker deployment
- Configure GPU node pool
- Build job orchestration

**Critical Files**:
- `src/infrastructure/k8s_manager.py`
- `k8s/workers/cpu-deployment.yaml`
- `k8s/workers/gpu-job.yaml`
- `Dockerfile`

### Phase 5: ML/CV Pipeline (Weeks 9-10)
**Goal**: Auto-detect and route ML workloads to GPU

Tasks:
- Implement ML workload detection
- Build GPU routing logic
- Create ML pipeline executor
- Test CV/ML tasks on GPU nodes
- Optimize resource allocation

**Critical Files**:
- `src/ml_pipeline/detector.py`
- `src/ml_pipeline/executor.py`
- `src/workers/gpu_detector.py`

### Phase 6: Integration & Testing (Weeks 11-12)
**Goal**: End-to-end validation and optimization

Tasks:
- End-to-end workflow testing
- Performance optimization
- Add monitoring (Prometheus/Grafana)
- Load testing
- Documentation
- Bug fixes

**Critical Files**:
- `tests/e2e/test_full_pipeline.py`
- `k8s/monitoring/prometheus.yaml`

## Critical Files to Create (Priority Order)

1. **src/skills/manager.py** ⭐ NEW
   - Skills loader and manager
   - Load skills from local directory
   - Skills execution interface

2. **src/agents/base.py**
   - Foundation for all agents
   - Claude API integration with skills support
   - Artifact management

3. **src/orchestration/master_agent.py**
   - Workflow orchestration
   - Task distribution
   - State management

4. **src/agents/uiux_designer.py** ⭐ NEW
   - UI/UX design system generation
   - Uses UI/UX Pro Max skill
   - Industry-specific design intelligence

5. **src/workers/worker.py**
   - Redis queue polling
   - Agent task execution
   - Result handling

6. **src/infrastructure/k8s_manager.py**
   - Kubernetes job creation
   - GPU resource allocation
   - Job monitoring

7. **src/agents/memory_agent.py**
   - Vector database integration
   - Pattern matching
   - Template suggestion

8. **src/ml_pipeline/detector.py**
   - ML workload detection
   - GPU requirement calculation
   - Routing decisions

9. **src/api/routes/projects.py**
   - REST API endpoints
   - Sales input handling
   - Status tracking

10. **web/src/components/RequirementsForm.tsx**
    - Sales UI
    - Requirement submission
    - Real-time status

11. **k8s/workers/gpu-job.yaml**
    - GPU pod specification
    - Resource limits
    - Node selectors

12. **docker-compose.yml**
    - Local development setup
    - Redis + PostgreSQL
    - Service orchestration

## Data Flow

### Input to Delivery
1. **Sales Input** → Web UI form submission
2. **API Gateway** → FastAPI validates and creates project
3. **Master Agent** → Initializes workflow, enqueues PRD task
4. **PRD Agent** → Queries memory for similar PRDs, generates document
5. **Solution Architect** → Designs architecture based on PRD
6. **Developer Agent** → Generates code
   - If ML/CV detected → GPU worker pod created
   - Else → CPU worker executes
7. **Parallel Execution**:
   - QA Engineer → Tests code
   - Security Engineer → Security scan
   - Tech Writer → Creates manual
   - Support Engineer → Writes docs
8. **Product/Project Managers** → Review all outputs
9. **Memory Agent** → Stores successful patterns
10. **Delivery** → Package and present to sales

### ML/CV Workload Routing
```
Requirements → ML Detector → Pattern Match
    ↓
    IF (ML/CV detected):
        → Calculate GPU requirements
        → Create Kubernetes GPU Job
        → Execute on V100/A100 node
    ELSE:
        → Route to CPU worker pool
```

## Key Design Decisions

### Why Redis for Queue?
- High-throughput message passing
- Native support for blocking pops (BRPOP)
- Pub/Sub for real-time notifications
- Battle-tested in production

### Why Kubernetes?
- Dynamic GPU node allocation
- Auto-scaling for CPU workers
- Resource isolation
- Production-grade orchestration

### Why ChromaDB?
- Python-native vector database
- Easy integration with sentence-transformers
- Persistent storage for patterns
- Fast similarity search

### Why PostgreSQL?
- ACID compliance for state management
- JSON support for flexible artifacts
- Strong consistency guarantees
- Mature ecosystem

## Missing Components (To Add)

Based on your requirements, here are potential enhancements:

1. **Agent Performance Metrics**
   - Track agent execution time
   - Success/failure rates per agent
   - Quality scores for outputs

2. **Human-in-the-Loop**
   - Approval gates at key stages
   - Manual review interface
   - Override capabilities

3. **Cost Tracking**
   - Track Claude API usage per project
   - GPU compute costs
   - Resource utilization reports

4. **Template Library**
   - Pre-built templates for common projects
   - Industry-specific patterns
   - Success rate tracking

5. **Rollback Mechanism**
   - Version control for artifacts
   - Ability to revert to previous stages
   - Audit trail

6. **Integration Hooks**
   - GitHub integration for code delivery
   - Slack notifications
   - Email updates

7. **Multi-tenancy**
   - Isolated workspaces per team
   - Resource quotas
   - Access control

## Verification Plan

### End-to-End Test Scenario
1. Submit sample requirement via Web UI
2. Verify PRD generation within 2 minutes
3. Confirm architecture document creation
4. Check code generation
5. For ML requirement: Verify GPU pod creation
6. Confirm parallel execution of QA/Security/Docs
7. Validate PM review completion
8. Ensure all artifacts saved to PostgreSQL
9. Verify memory agent stored patterns
10. Check final delivery package

### Success Metrics
- **Workflow completion**: < 30 minutes for typical project
- **GPU utilization**: > 70% when ML workload present
- **Memory recall**: > 80% similarity for matching patterns
- **Agent success rate**: > 95% task completion
- **API latency**: < 200ms for non-LLM endpoints

### Test Commands
```bash
# Start local environment
docker-compose up -d

# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run E2E test
pytest tests/e2e/test_full_pipeline.py -v

# Check Kubernetes cluster
kubectl get pods -n swe-engine

# Monitor GPU utilization
kubectl top nodes --selector=accelerator=nvidia-tesla-v100

# View agent metrics
curl http://localhost:8000/api/monitoring/agents

# Test ML workload detection
python -m swe_engine.ml_pipeline.detector --test
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Claude API rate limits | High | Implement retry logic, queue throttling |
| GPU node shortage | High | Fallback to CPU, queue GPU jobs |
| Agent task failures | Medium | Retry mechanism, error handling |
| Memory system drift | Medium | Periodic retraining, quality scoring |
| Kubernetes cluster failure | High | Multi-region deployment, backups |
| Cost overruns | Medium | Budget alerts, resource limits |

## Next Steps After Approval

1. **Copy plan to agent_bus repository and push**
   - `cp /home/bot/.claude/plans/sequential-finding-sprout.md /home/bot/Desktop/bot/agent_bus/PLAN.md`
   - `cd /home/bot/Desktop/bot/agent_bus && git add PLAN.md && git commit -m "Add initial planning document" && git push`
2. Navigate to agent_bus repository (`cd /home/bot/Desktop/bot/agent_bus`)
3. Set up Python project with Poetry (`poetry init`)
4. Create directory structure (`mkdir -p src/{agents,orchestration,workers,infrastructure,ml_pipeline,skills,api}`)
5. Install Claude Skills locally in `skills/` directory
6. Create Docker Compose for local development
7. Implement BaseAgent and MasterAgent
8. Build first agent (PRD) as proof of concept
9. Set up CI/CD pipeline
