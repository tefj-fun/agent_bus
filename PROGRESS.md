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

## QA
### Docker (repeatable)
```bash
cd agent_bus
docker compose up -d --build
# run tests inside the api image
docker compose run --rm api pytest -q
```
Result: PASS (9 passed) on 2026-01-31

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
