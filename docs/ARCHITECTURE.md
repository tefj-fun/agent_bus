# Agent Bus Architecture

## Service Split: API / Worker / Orchestrator

The agent_bus platform is designed as a distributed system with three primary service types:

### 1. API Service
**Responsibility:** HTTP API endpoints, request handling, job submission

**Components:**
- FastAPI application
- REST endpoints for job management
- Authentication middleware
- Rate limiting
- Request validation

**Endpoints:**
- `POST /jobs` - Submit new job
- `GET /jobs/{id}` - Get job status
- `GET /jobs/{id}/results` - Retrieve results
- `POST /memory/store` - Store memory
- `GET /memory/search` - Search memory

**Deployment:**
- Stateless (can scale horizontally)
- Multiple replicas behind load balancer
- Auto-scaling based on request rate

**Resource Requirements:**
- CPU: 0.5-1 core per replica
- Memory: 512MB-1GB per replica

### 2. Worker Service
**Responsibility:** Execute agent tasks

**Components:**
- Task consumer (pulls from Redis queue)
- Agent executor
- Result publisher
- Health reporter

**Workflow:**
1. Poll Redis for tasks
2. Execute task (run agent)
3. Store results in PostgreSQL
4. Publish completion event

**Deployment:**
- Multiple replicas on standard nodes
- Can scale horizontally based on queue depth

**Resource Requirements:**
- CPU: 1-2 cores per worker
- Memory: 2-4GB per worker

### 3. Orchestrator Service
**Responsibility:** Job coordination, routing, HITL, observability

**Components:**
- Master agent (coordinates sub-agents)
- Task routing logic
- Human-in-the-loop (HITL) coordination
- Monitoring and metrics aggregation

**Workflow:**
1. Receive job from API
2. Break down into tasks
3. Route tasks to workers
4. Coordinate HITL interventions
5. Aggregate results

**Deployment:**
- Single replica or active-passive HA pair
- Stateful (maintains job state)

**Resource Requirements:**
- CPU: 1-2 cores
- Memory: 2-4GB

## Communication Patterns

### Message Queue (Redis)
- API → Orchestrator: Job submissions
- Orchestrator → Workers: Task assignments
- Workers → Orchestrator: Task completions

### Database (PostgreSQL)
- API: Read job status
- Orchestrator: Read/write job state, memory
- Workers: Write results, read memory

### Direct HTTP (optional)
- API → Orchestrator: Real-time status updates
- Orchestrator → Workers: Health checks

## System Architecture

```
┌─────────┐      ┌─────────────┐      ┌──────────────┐
│  User   │─────▶│     API     │─────▶│ Orchestrator │
└─────────┘      └──────┬──────┘      └──────┬───────┘
                        │                    │
                        │              ┌─────▼─────┐
                        │              │   Redis   │
                        │              └─────┬─────┘
                        │                    │
                        │              ┌─────▼─────┐
                        │              │  Workers  │
                        │              └─────┬─────┘
                        │                    │
                        └────────┬───────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
               ┌────▼────┐ ┌────▼────┐ ┌─────▼─────┐
               │PostgreSQL│ │ChromaDB │ │ Artifacts │
               └──────────┘ └─────────┘ └───────────┘
```

**Data Flow:**
1. User submits requirements via API
2. Orchestrator creates job and queues tasks in Redis
3. Workers pull tasks, execute agents, store results
4. All services share PostgreSQL (state) and ChromaDB (memory)

## Benefits of Service Split

1. **Scalability:** Scale API and workers independently
2. **Fault Isolation:** API failure doesn't affect worker execution
3. **Deployment Flexibility:** Update services independently
4. **Resource Efficiency:** Workers can be sized appropriately for workload

## Implementation Status

- ✅ API service structure exists (`src/api/`)
- ✅ Worker skeleton exists (`src/workers/`)
- ✅ Orchestrator logic exists (`src/orchestration/`)
- ✅ Service separation is logical and enforced via docker-compose

## Next Steps

1. Enforce service boundaries with clear interfaces
2. Implement inter-service authentication
3. Add circuit breakers for resilience
4. Deploy monitoring per service
