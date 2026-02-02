# Agent Bus Architecture (KAN-63)

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
- No GPU required

### 2. Worker Service
**Responsibility:** Execute tasks (CPU and GPU workloads)

**Types:**
- **CPU Workers:** General purpose task execution
- **GPU Workers:** ML/CV workload execution with GPU acceleration

**Components:**
- Task consumer (pulls from Redis queue)
- Workload executor
- Result publisher
- Health reporter

**Workflow:**
1. Poll Redis for tasks
2. Execute task (run agent, ML model, etc.)
3. Store results in PostgreSQL
4. Publish completion event

**Deployment:**
- CPU Workers: Multiple replicas, standard nodes
- GPU Workers: Single replica per GPU node, with GPU resource allocation

**Resource Requirements:**
- CPU Workers: 1-2 cores, 2-4GB RAM
- GPU Workers: 2-4 cores, 8-16GB RAM, 1 GPU

### 3. Orchestrator Service
**Responsibility:** Job coordination, routing, HITL, observability

**Components:**
- Master agent (coordinates sub-agents)
- GPU routing logic
- Human-in-the-loop (HITL) coordination
- Monitoring and metrics aggregation

**Workflow:**
1. Receive job from API
2. Break down into tasks
3. Route tasks to appropriate workers (CPU/GPU)
4. Coordinate HITL interventions
5. Aggregate results

**Deployment:**
- Single replica or active-passive HA pair
- Stateful (maintains job state)

**Resource Requirements:**
- CPU: 1-2 cores
- Memory: 2-4GB
- No GPU required

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

## Deployment Topology

```
                    ┌─────────────┐
                    │ Load        │
                    │ Balancer    │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
       ┌────▼────┐    ┌───▼────┐    ┌───▼────┐
       │ API     │    │ API    │    │ API    │
       │ Pod 1   │    │ Pod 2  │    │ Pod N  │
       └────┬────┘    └───┬────┘    └───┬────┘
            │             │             │
            └─────────────┼─────────────┘
                          │
                    ┌─────▼──────┐
                    │ Redis      │
                    │ Queue      │
                    └─────┬──────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
       ┌────▼────┐   ┌───▼────┐   ┌───▼────┐
       │Orchestr-│   │CPU     │   │GPU     │
       │ator     │   │Worker  │   │Worker  │
       └────┬────┘   └───┬────┘   └───┬────┘
            │            │            │
            └────────────┼────────────┘
                         │
                    ┌────▼──────┐
                    │PostgreSQL │
                    │           │
                    └───────────┘
```

## Benefits of Service Split

1. **Scalability:** Scale API, CPU, and GPU workers independently
2. **Resource Efficiency:** GPU workers only where needed
3. **Fault Isolation:** API failure doesn't affect worker execution
4. **Deployment Flexibility:** Update services independently
5. **Cost Optimization:** Run GPU workers only when needed

## Implementation Status

- ✅ API service structure exists (`src/api/`)
- ✅ Worker skeleton exists (`src/workers/`)
- ✅ Orchestrator logic exists (`src/orchestration/`)
- ⚠️  Service separation is logical, not fully enforced
- 🔄 Deployment configs support separation (docker-compose, k8s)

## Next Steps

1. Enforce service boundaries with clear interfaces
2. Implement inter-service authentication
3. Add circuit breakers for resilience
4. Deploy monitoring per service
5. Add service mesh (Istio/Linkerd) for advanced routing
