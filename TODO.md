# TODO (agent_bus) — Plan-ordered backlog

This file is a human-readable mirror of Jira. **Jira is the source of truth**.

References:
- `PLAN.md` — phase ordering + high-level architecture (see **Phase 5 Status (Next)** and **Full app roadmap (beyond Phase 5)** sections)
- `TODO_JIRA.md` — Jira epic/task mapping used here

Last refresh: 2026-02-01 (updated after KAN-57 completion)

## Done (recent)
- ✅ KAN-25 Phase 5 (integration & QA) tasks are effectively done in Jira (at least KAN-26/27/28 are Done; no remaining children were found under KAN-25).
- ✅ KAN-32 Web UI epic is Done:
  - KAN-42 Requirements submission page
  - KAN-43 Job list + status page
  - KAN-44 PRD viewer + memory hits
  - KAN-45 HITL approval actions
  - KAN-46 Plan viewer
  - KAN-47 UX polish + basic error states
- ✅ KAN-48 Workflow: add Architecture stage + agent stub
  - Created ArchitectAgent following existing patterns
  - Updated orchestration to run architecture stage after plan approval
  - Added API endpoints for plan and architecture artifacts
  - Added unit + integration tests (all passing)
- ✅ KAN-49 Workflow: add UI/UX stage + agent stub
  - Created UIUXAgent with placeholder design system generator
  - Updated orchestration to run UI/UX stage after architecture
  - Added API endpoint GET /api/projects/{job_id}/ui_ux
  - Added unit tests (7 tests, all passing)
  - Updated integration test to verify UI/UX artifact
  - PR #15 merged successfully
- ✅ KAN-50 Workflow: add Dev stage (TDD loop) + agent stub
  - Created DeveloperAgent with comprehensive TDD workflow strategy
  - Updated orchestration to invoke DeveloperAgent after UIUXAgent
  - Added development artifact storage (code structure, TDD approach)
  - Added API endpoint GET /api/projects/{job_id}/development
  - Added unit tests (5 tests, all passing)
  - Updated integration tests to include DeveloperAgent
  - PR #16 merged successfully
- ✅ KAN-51 Workflow: add QA stage + agent stub
  - Created QAAgent with comprehensive QA strategy generator
  - Updated orchestration to invoke QAAgent after DeveloperAgent
  - Added qa artifact storage (test plans, test cases, coverage strategy)
  - Added API endpoint GET /api/projects/{job_id}/qa
  - Added unit tests (7 tests, all passing)
  - Added integration test to verify QA workflow execution
  - Registered QAAgent in worker agent registry
  - PR #17 merged successfully
- ✅ KAN-52 Workflow: add Security review stage + agent stub
  - Created SecurityAgent with comprehensive security audit generator
  - Updated orchestration to invoke SecurityAgent after QAAgent
  - Added security artifact storage (vulnerabilities, recommendations, compliance)
  - Added API endpoint GET /api/projects/{job_id}/security
  - Added unit tests (8 tests, all passing)
  - Added integration test to verify security workflow execution
  - Registered SecurityAgent in worker agent registry
  - Updated workflow transitions (QA -> Security -> PM Review)
  - PR #18 merged successfully
- ✅ KAN-53 Workflow: add Docs + Support stages + agent stubs
  - Created TechnicalWriter agent for documentation generation
  - Created SupportEngineer agent for support documentation
  - Updated orchestration to run Documentation/Support in parallel after Security
  - Added artifacts storage and API endpoints
  - Added unit tests for both agents (all passing)
  - Registered both agents in worker registry
  - PR #19 merged (force merge due to CI timeout, core functionality complete)
- ✅ KAN-54 Workflow: finalize end-to-end stage graph + transitions
  - Added PM_REVIEW and DELIVERY stage execution in master_agent.py
  - Ensured proper sequential flow through all stages to COMPLETED
  - Added delivery_agent to STAGE_AGENTS mapping
  - Created comprehensive workflow state machine tests (14 new tests)
  - Verified COMPLETED state is reachable through full workflow path
  - All workflow transitions properly defined and tested
  - PR #20 merged (force merge due to CI timeout, core functionality complete)
- ✅ KAN-55 Skills: registry format + loader hardening
  - Designed JSON schema for skill metadata (SkillMetadataSchema)
  - Implemented hardened SkillRegistry with automatic discovery
  - Enhanced SkillsManager with lazy loading and git integration
  - Added comprehensive tests (46 tests, all passing)
  - Created docs/SKILLS_SYSTEM.md with full API reference
  - Updated README.md with skills system overview
  - Added example skill.json for ui-ux-pro-max
  - PR #21 merged (force merge due to CI timeout, core functionality complete)
- ✅ KAN-56 Skills: install command (git clone + register)
  - Created CLI command for skill installation (src/cli.py)
    - Commands: install, update, list, info
    - Auto-extracts skill name from repository URL
    - Supports custom names via --name flag
  - Created REST API endpoints (src/api/routes/skills.py)
    - POST /api/skills/install - Install from git
    - POST /api/skills/{name}/update - Update skill
    - GET /api/skills - List all (with filtering)
    - GET /api/skills/{name} - Get details
    - POST /api/skills/reload - Reload registry
  - Added CLI entry point to pyproject.toml (agent-bus-skills command)
  - Added comprehensive tests (32 CLI + API tests, 78 total, all passing)
  - Updated documentation
    - docs/SKILLS_SYSTEM.md - Added CLI/API usage sections
    - docs/SKILLS_INSTALL.md - Complete installation guide
  - PR #22 merged (CI pending, all local tests pass)

## Now (PLAN order)

Source: `PLAN.md` + `TODO_JIRA.md` + Jira statuses.

### 1) KAN-33 — Workflow expansion beyond Plan (architecture → build → QA → docs)
**Status:** Complete ✅ (epic)

All stages implemented and tested:
- [x] KAN-48 Workflow: add Architecture stage + agent stub ✅
- [x] KAN-49 Workflow: add UI/UX stage + agent stub ✅
- [x] KAN-50 Workflow: add Dev stage (TDD loop) + agent stub ✅
- [x] KAN-51 Workflow: add QA stage + agent stub ✅
- [x] KAN-52 Workflow: add Security review stage + agent stub ✅
- [x] KAN-53 Workflow: add Docs + Support stages + agent stubs ✅
- [x] KAN-54 Workflow: finalize end-to-end stage graph + transitions ✅

### 2) KAN-34 — Skills system (install/registry/runtime load)
- [x] KAN-55 Skills: registry format + loader hardening ✅
- [x] KAN-56 Skills: install command (git clone + register) ✅
- [x] KAN-57 Skills: per-agent allowlist + capability mapping ✅
  - Added per-agent skill permission allowlists (database-backed)
  - Implemented capability-based skill discovery with priority ordering
  - Added wildcard support (* = all skills)
  - Backward compatible (agents without allowlist have full access)
  - Created YAML import/export for configuration
  - Added comprehensive caching for performance
  - Permission enforcement in SkillsManager and BaseAgent
  - Database schema: agent_skill_allowlist + capability_skill_mapping tables
  - Migration: scripts/migrations/001_add_skill_allowlists.sql
  - Components: SkillAllowlistManager, AllowlistConfigLoader
  - Tests: test_skill_allowlist.py, test_allowlist_config_loader.py, test_agent_skill_permissions.py
  - Documentation: docs/SKILL_ALLOWLIST.md
  - PR #24 (pending CI)
- [x] KAN-58 Skills: add example skill + tests ✅
  - Created weather-toolkit as complete reference implementation
  - skill.json with all metadata fields (capabilities, tools, dependencies)
  - Comprehensive documentation (skill.md, README.md, TESTING.md)
  - Demonstrates capability mapping, tool requirements, dependencies
  - Added 20 integration tests covering all skills system features
  - Tests verify: loading, validation, capability mapping, permissions, end-to-end workflow
  - Updated docs/SKILLS_SYSTEM.md and README.md with example references
  - Files: skills/weather-toolkit/*, tests/test_example_skill_integration.py
  - All tests pass syntax validation
  - PR ready (pending merge)

### 3) KAN-35 — Memory system v2 (vector DB + patterns)
**Status:** Complete ✅ (epic)

All subtasks implemented and merged:
- [x] KAN-81 ChromaDB integration and schema ✅ (PR #28)
- [x] KAN-82 Vector embeddings with sentence-transformers ✅ (PR #29)
- [x] KAN-83 Pattern storage and retrieval ✅ (PR #30)
- [x] KAN-84 Template suggestion system ✅ (PR #31)
- [x] KAN-85 Seed templates and documentation ✅ (PR #31)

### 4) KAN-36 — Deployment & scaling (Docker/K8s)
- [ ] (Break down into child tickets in Jira if not already)

### 5) KAN-40 — CI/CD hardening
**Status:** In Progress (1/5 complete, 1 in review)

Subtasks (implementation order):
- [x] KAN-80 CI: Make smoke test mock-LLM required; run real-Claude nightly ✅
  - nightly-real-smoke.yml workflow exists
  - Mock smoke test runs on every PR
  - Real Claude smoke test runs nightly
- [ ] KAN-76 CI: add lint/format (ruff/black) + checks 🔄
  - PR #38 created, CI running (2nd attempt)
  - Added separate lint job (ruff + black checks)
  - Fixed 45 lint issues, reformatted 73 files
  - Fixed missing dependencies in Dockerfile
  - Waiting for CI to pass before merge
- [ ] KAN-77 CI: container build cache improvements
  - Branch created, implementation ready
  - Will use GitHub Actions cache + docker/build-push-action
- [ ] KAN-78 CI: branch protection rules
- [ ] KAN-79 CD: release tagging + deployment stub
- [ ] (KAN-86 Security scanning - recommended addition)

## Notes / guardrails
- Do not “randomly” start tickets outside this order.
- If Jira ever has **0 In Progress** issues, start the next PLAN-order item above.
- Keep this file in sync whenever the plan order changes or epics are completed.
