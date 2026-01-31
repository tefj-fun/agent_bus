# Progress

## Phase 1 - Complete
- [x] PRD agent implemented
- [x] Master orchestration + PRD-only workflow
- [x] Worker plumbing and Redis/Postgres integration
- [x] Docker Compose dev setup

## Phase 2 - Complete
- [x] Technical Writer agent
- [x] Support Engineer agent
- [x] Product Manager agent
- [x] Project Manager agent
- [x] Memory Agent (ChromaDB optional + in-memory fallback)
- [x] Worker registry updated for new agents
- [x] Minimal tests for new agents and registry

## Phase 3 - In Progress
- [x] Postgres-backed TF-IDF memory store (no external embeddings)
- [x] Memory API endpoints (health/query/upsert)
- [x] PRD agent memory retrieval + persistence
- [x] Tests for deterministic memory queries + PRD memory integration
- [x] Memory smoke script

## Phase 4 - Complete
- [x] Async project creation with queued jobs
- [x] Job status endpoint includes timestamps + workflow stage
- [x] PRD retrieval endpoint with artifacts/tasks fallback
- [x] Memory hits captured + exposed during PRD generation
- [x] HITL approval gate + approve/request_changes endpoints
- [x] PlanAgent generates plan artifacts after approval

## QA Records

### 2026-01-31 — Unit tests (Docker)
```bash
cd agent_bus
docker compose up -d --build
docker compose run --rm api pytest -q
```
Result: **FAIL** — Docker not available (`/var/run/docker.sock` permission denied).

### 2026-01-31 — Smoke script (async flow)
```bash
curl -sS -X POST http://localhost:8000/api/projects/ \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"phase4_async","requirements":"PRD for a lightweight bug tracker with tags, search, and SLAs."}'

# Poll status (replace job_id from create response)
curl -sS http://localhost:8000/api/projects/{job_id}

# Fetch latest PRD
curl -sS http://localhost:8000/api/projects/{job_id}/prd

# Fetch memory hits
curl -sS http://localhost:8000/api/projects/{job_id}/memory_hits

# Approve and kick off plan stage
curl -sS -X POST http://localhost:8000/api/projects/{job_id}/approve \
  -H 'Content-Type: application/json' \
  -d '{"notes":"Looks good. Proceed to planning."}'
```
Result: **PENDING** — requires Docker runtime.

### 2026-01-31 — Smoke test (PRD-only)
```bash
curl -sS -X POST http://localhost:8000/api/projects/ \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"phase2_smoke","requirements":"Write a short PRD for a notes app with tags and search."}'
```
Verify:
- PRD content exists in `tasks.output_data->>'prd_content'`
- Artifact row exists in `artifacts` with `type='prd'`

Result: **PASS** (historical Phase 3 run; not re-run due to Docker constraints)

### 2026-01-31 — Smoke test (memory endpoints)
```bash
./scripts/memory_smoke.sh
```
Expected:
- `/api/memory/health` returns backend `postgres_tfidf`
- upsert returns doc_id
- query returns results with score

Result: **PASS** (historical Phase 3 run; not re-run due to Docker constraints)
