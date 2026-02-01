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
Result: **PASS** (11 passed, 23 warnings)

### 2026-01-31 — Smoke script (async flow)
```bash
cd agent_bus
docker compose up -d --build
./scripts/phase4_smoke.sh
```
Result: **PASS** (local Docker) — verifies:
- queued → prd_generation → waiting_for_approval → approve → plan_generation → completed
- PRD content accessible via `/api/projects/{job_id}/prd`
- memory hits accessible via `/api/projects/{job_id}/memory_hits`

### 2026-01-31 — CI (GitHub Actions)
- Added `.github/workflows/ci.yml`
- Gates:
  - `pytest -q` (docker compose)
  - `./scripts/phase4_smoke.sh` (required) in **mock LLM** mode (0 tokens)
- Added `.github/workflows/nightly-real-smoke.yml`:
  - scheduled/manual **real-Claude** smoke (requires `ANTHROPIC_API_KEY` secret)
Result: **PASS**

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
