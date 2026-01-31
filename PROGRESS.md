# Progress

## Phase 1 - Complete
- [x] PRD agent implemented
- [x] Master orchestration + PRD-only workflow
- [x] Worker plumbing and Redis/Postgres integration
- [x] Docker Compose dev setup

## Phase 2 - In Progress
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

## QA
### Docker (repeatable)
```bash
cd agent_bus
docker compose up -d --build
# run tests inside the api image
docker compose run --rm api pytest -q
```
Result: FAIL (docker socket permission denied) on 2026-01-31

### Smoke test (PRD-only)
```bash
curl -sS -X POST http://localhost:8000/api/projects/ \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"phase2_smoke","requirements":"Write a short PRD for a notes app with tags and search."}'
```
Verify:
- PRD content exists in tasks.output_data->>'prd_content'
- Artifact row exists in artifacts table with type='prd'

Result: PASS on 2026-01-31

### Smoke test (memory)
```bash
./scripts/memory_smoke.sh
```
Result: NOT RUN (docker required) on 2026-01-31
