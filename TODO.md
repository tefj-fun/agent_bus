# TODO (agent_bus) — Plan-ordered backlog

This file is a human-readable mirror of Jira. **Jira is the source of truth**.

References:
- `PLAN.md` — phase ordering + high-level architecture (see **Phase 5 Status (Next)** and **Full app roadmap (beyond Phase 5)** sections)
- `TODO_JIRA.md` — Jira epic/task mapping used here

Last refresh: 2026-02-01

## Done (recent)
- ✅ KAN-25 Phase 5 (integration & QA) tasks are effectively done in Jira (at least KAN-26/27/28 are Done; no remaining children were found under KAN-25).
- ✅ KAN-32 Web UI epic is Done:
  - KAN-42 Requirements submission page
  - KAN-43 Job list + status page
  - KAN-44 PRD viewer + memory hits
  - KAN-45 HITL approval actions
  - KAN-46 Plan viewer
  - KAN-47 UX polish + basic error states

## Now (PLAN order)

Source: `PLAN.md` + `TODO_JIRA.md` + Jira statuses.

### 1) KAN-33 — Workflow expansion beyond Plan (architecture → build → QA → docs)
**Status:** In Progress (epic)

Do these in order:
- [ ] KAN-48 Workflow: add Architecture stage + agent stub
- [ ] KAN-49 Workflow: add UI/UX stage + agent stub
- [ ] KAN-50 Workflow: add Dev stage (TDD loop) + agent stub
- [ ] KAN-51 Workflow: add QA stage + agent stub
- [ ] KAN-52 Workflow: add Security review stage + agent stub
- [ ] KAN-53 Workflow: add Docs + Support stages + agent stubs
- [ ] KAN-54 Workflow: finalize end-to-end stage graph + transitions

### 2) KAN-34 — Skills system (install/registry/runtime load)
- [ ] KAN-55 Skills: registry format + loader hardening
- [ ] KAN-56 Skills: install command (git clone + register)
- [ ] KAN-57 Skills: per-agent allowlist + capability mapping
- [ ] KAN-58 Skills: add example skill + tests

### 3) KAN-35 — Memory system v2 (vector DB + patterns)
- [ ] (Break down into child tickets in Jira if not already)

### 4) KAN-36 — Deployment & scaling (Docker/K8s)
- [ ] (Break down into child tickets in Jira if not already)

### 5) KAN-40 — CI/CD hardening
- [ ] KAN-79 CD: release tagging + deployment stub
- [ ] (Other KAN-40 children as created)

## Notes / guardrails
- Do not “randomly” start tickets outside this order.
- If Jira ever has **0 In Progress** issues, start the next PLAN-order item above.
- Keep this file in sync whenever the plan order changes or epics are completed.
