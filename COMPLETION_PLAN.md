# Agent Bus - Completion Plan

## Current Status (2026-02-01)

### ✅ Complete
- Phase 1-4: Core system (FastAPI, Redis, PostgreSQL, agents, workflow, HITL)
- KAN-33: Full workflow stages (Architecture → UI/UX → Dev → QA → Security → Docs/Support → Finalize)
- KAN-34: Skills system (registry, install, permissions, example weather-toolkit)
- KAN-35: Memory v2 (ChromaDB, embeddings, pattern storage, templates, 5 seeds)
- Basic Dockerfile (being fixed in PR #39)

### ⏳ Remaining Work

## 1. Infrastructure & Deployment (High Priority)

### 1.1 Kubernetes Manifests
**Location:** `k8s/base/`
**Files to Create:**
- `api-deployment.yaml` - FastAPI application deployment
- `cpu-worker-deployment.yaml` - CPU worker pool
- `redis-deployment.yaml` - Redis StatefulSet
- `postgres-deployment.yaml` - PostgreSQL StatefulSet
- `configmap.yaml` - Configuration
- `secrets.yaml` - Secrets template
- `service-api.yaml` - API LoadBalancer/NodePort
- `service-redis.yaml` - Redis ClusterIP
- `service-postgres.yaml` - PostgreSQL ClusterIP
- `namespace.yaml` - agent-bus namespace
- `kustomization.yaml` - Kustomize base

**Already exists:**
- ✅ `gpu-worker-job.yaml` - GPU job template

### 1.2 Kustomize Overlays
**Location:** `k8s/overlays/`
**Directories:**
- `dev/` - Development overlay (small resources, local storage)
- `production/` - Production overlay (HA, replicas, persistent volumes)

**Files per overlay:**
- `kustomization.yaml`
- `patches.yaml`
- Environment-specific values

### 1.3 Helm Charts
**Location:** `helm/agent-bus/`
**Files to Create:**
- `Chart.yaml` - Chart metadata
- `values.yaml` - Default values
- `values-dev.yaml` - Dev overrides
- `values-prod.yaml` - Production overrides
- `templates/api-deployment.yaml`
- `templates/worker-deployment.yaml`
- `templates/gpu-worker-job.yaml`
- `templates/redis-statefulset.yaml`
- `templates/postgres-statefulset.yaml`
- `templates/services.yaml`
- `templates/configmap.yaml`
- `templates/secrets.yaml`
- `templates/ingress.yaml`
- `templates/_helpers.tpl`

### 1.4 Docker Optimization
**Status:** Basic Dockerfile exists, dependencies being fixed
**Enhancements Needed:**
- Multi-stage build (builder + runtime)
- Layer caching optimization
- Security hardening (non-root user)
- Health check integration

## 2. ML/CV Pipeline (Medium Priority)

### 2.1 ML Workload Detection
**File:** `src/ml_pipeline/detector.py`
**Functionality:**
- Analyze PRD/requirements for ML/CV keywords
- Score ML likelihood (0-1)
- Identify required resources (CPU/GPU, memory)
- Return routing decision

### 2.2 GPU Job Orchestration
**File:** `src/ml_pipeline/executor.py`
**Functionality:**
- Create Kubernetes GPU Job from template
- Monitor job status
- Collect results
- Handle failures/retries

### 2.3 Integration with Master Agent
**File:** `src/orchestration/master_agent.py`
**Changes:**
- Check ML workload before routing to worker
- Route ML tasks to GPU executor
- Route non-ML to CPU worker pool

## 3. Observability & Monitoring (Medium Priority)

### 3.1 Prometheus Metrics
**File:** `src/infrastructure/metrics.py`
**Metrics:**
- `agent_bus_projects_total` - Total projects created
- `agent_bus_projects_by_stage` - Projects by stage (gauge)
- `agent_bus_stage_duration_seconds` - Stage completion time (histogram)
- `agent_bus_agent_invocations_total` - Agent invocations by type
- `agent_bus_llm_tokens_total` - LLM tokens consumed
- `agent_bus_llm_cost_dollars` - Estimated cost
- `agent_bus_errors_total` - Errors by type
- `agent_bus_redis_queue_depth` - Tasks in queue

**Integration:**
- FastAPI `/metrics` endpoint
- Prometheus middleware

### 3.2 Grafana Dashboards
**Location:** `k8s/monitoring/`
**Files:**
- `grafana-dashboard-overview.json` - System overview
- `grafana-dashboard-agents.json` - Agent performance
- `grafana-dashboard-costs.json` - LLM cost tracking

### 3.3 Logging
**Standardization:**
- Structured JSON logging
- Log levels configuration
- Correlation IDs across workflow
- ELK/Loki integration ready

## 4. CI/CD Improvements (Low Priority)

### 4.1 Lint & Format Checks
**File:** `.github/workflows/ci.yml`
**Add:**
- Black formatting check
- Ruff linting
- MyPy type checking
- Fail on violations

### 4.2 Build Caching
**Docker layer caching in GitHub Actions**
- Use `docker/build-push-action@v5` with caching
- Cache pip dependencies
- Cache pre-commit hooks

### 4.3 Release Automation
**File:** `.github/workflows/release.yml`
**Trigger:** Git tag `v*`
**Actions:**
- Build Docker image
- Tag with version + latest
- Push to registry (GHCR/DockerHub)
- Create GitHub Release with changelog
- Deploy to staging (optional)

## 5. Testing & Validation (Medium Priority)

### 5.1 E2E Smoke Test
**Status:** Phase 4 smoke test exists, moved to manual workflow
**Enhancements:**
- Add more comprehensive test scenarios
- Test ML workload routing
- Test skills loading
- Test memory retrieval

### 5.2 Load Testing
**Tool:** Locust or k6
**Scenarios:**
- Concurrent project creation
- High-throughput workflow execution
- Memory system stress test
- Redis queue saturation

### 5.3 Integration Tests
**Status:** Some exist, some skip in CI
**Improvements:**
- Run all tests in CI (fix timeouts)
- Add tests for new K8s integration
- Add tests for ML pipeline
- Improve test isolation

## 6. Documentation (Low Priority)

### 6.1 Deployment Guide
**File:** `docs/DEPLOYMENT.md`
**Content:**
- Prerequisites (K8s cluster, kubectl, helm)
- Installation steps
- Configuration options
- Troubleshooting

### 6.2 Operations Guide
**File:** `docs/OPERATIONS.md`
**Content:**
- Scaling workers
- Monitoring dashboards
- Log analysis
- Common issues

### 6.3 Architecture Diagram
**Update:** `docs/ARCHITECTURE.md`
**Add:**
- System diagram (components + connections)
- Workflow state machine diagram
- Deployment topology

## Implementation Order

### Phase A: Critical Path (Do First)
1. Fix CI (PR #39) ✅ In Progress
2. Create complete K8s base manifests
3. Create Kustomize overlays (dev + prod)
4. Create Helm chart basics
5. Test local deployment with docker-compose
6. Test K8s deployment with minikube/kind

### Phase B: Feature Complete (Do Next)
7. ML workload detector
8. GPU job executor
9. Integrate ML pipeline with orchestrator
10. Prometheus metrics
11. Grafana dashboards
12. Docker multi-stage optimization

### Phase C: Polish (Do Last)
13. CI lint/format checks
14. Build caching
15. Release automation
16. Load testing
17. Documentation updates
18. Final E2E validation

## Success Criteria

### Minimum Viable Complete (MVC)
- ✅ All workflow stages functional
- ✅ Skills system working
- ✅ Memory system working
- ✅ CI passing
- 🎯 K8s manifests complete
- 🎯 Helm chart deployable
- 🎯 ML pipeline routing functional
- 🎯 Basic observability (metrics endpoint)

### Production Ready
- Docker optimized (multi-stage)
- All CI checks passing (lint, format, types)
- Comprehensive monitoring dashboards
- Load tested (100+ concurrent projects)
- Documentation complete
- Release automation working

## Timeline Estimate

**Phase A:** 2-3 hours (K8s infrastructure)
**Phase B:** 3-4 hours (ML pipeline + observability)
**Phase C:** 2-3 hours (polish + validation)

**Total:** 7-10 hours for feature-complete system
**Total:** 12-15 hours for production-ready system

## Notes

- Focus on getting K8s deployment working first
- ML pipeline can be stubbed initially (always route to CPU until GPU logic is complete)
- Observability can start with just metrics endpoint (dashboards can come later)
- CI improvements are nice-to-have but not blocking for completion
