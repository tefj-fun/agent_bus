# TODO (agent_bus) — Phase 5+ backlog

Source: PLAN.md Phase 5 (integration & end-to-end stability) + CI follow-ups.

## Now (next PRs)

(Jira: KAN-25 epic + tasks KAN-26..KAN-30)

### 1) API contract: memory_hits should be proper JSON
- [ ] Change `/api/projects/{job_id}/memory_hits` to return `memory_hits` as a JSON array (not a JSON-encoded string)
- [ ] Add unit/integration test to assert response schema + types
- [ ] Update smoke script accordingly (can remove the json.loads() fallback once API is fixed)

### 2) Add pytest integration tests for async + HITL flow
- [ ] Add integration test: create project → wait waiting_for_approval → fetch PRD → approve → wait completed
- [ ] Assert artifacts exist:
  - `GET /api/projects/{job_id}/prd` returns content
  - `GET /api/projects/{job_id}/plan` (if exists) or artifact row for plan exists
- [ ] Add failure-mode test: bad requirements / missing LLM key returns failed with actionable error

### 3) Orchestration resiliency (API restarts)
- [ ] Move orchestration loop out of the FastAPI process into a dedicated service (e.g., `orchestrator` container)
- [ ] Ensure jobs continue after API restart (no in-process background task dependency)
- [ ] Add integration test: start job → restart api container → job still completes

## CI / DevEx
- [ ] Fix GitHub Actions annotation: occasional `git exit code 128` (likely during teardown/log collection) — investigate and eliminate noise
- [ ] Add branch protection rule: require CI for `main` merges

## LLM provider switch (Codex/Claude)
- [ ] Add config setting `LLM_PROVIDER=anthropic|openai`
- [ ] Implement OpenAI client wrapper alongside `anthropic_client.py`
- [ ] Refactor `BaseAgent.query_llm()` to use provider-agnostic interface
- [ ] Add tests for selection logic (mocked)
- [ ] Keep Phase 4 smoke required in CI; update to run against selected provider(s) as desired

## Notes
- CI currently requires `ANTHROPIC_API_KEY` secret for the smoke test.
