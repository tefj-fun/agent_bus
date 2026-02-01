#!/usr/bin/env python3
"""Seed execution-ready Jira stories under the roadmap epics (KAN-32..KAN-40).

- Reads Jira creds from /home/bot/.moltbot/secrets/jira.env
- Uses Jira Cloud endpoint /rest/api/3/search/jql (GET /search returns 410)
- Links stories to epics via fields.parent = {key: <EPIC_KEY>} (team-managed project behavior)
- Idempotent: reuses existing issues with exact summary match.

Safe: does NOT print secrets.
"""

import os
import json
import base64
from pathlib import Path
from urllib import request


def load_env(path: str):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)


def adf(text: str) -> dict:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def jira_req(method: str, url: str, email: str, token: str, payload=None, timeout=60):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode(),
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body) if body else {}


def jira_search(base_url: str, email: str, token: str, jql: str, fields=None, max_results=10):
    url = f"{base_url}/rest/api/3/search/jql"
    payload = {
        "jql": jql,
        "maxResults": max_results,
    }
    if fields:
        payload["fields"] = fields
    _, out = jira_req("POST", url, email, token, payload, timeout=60)
    return out


def ensure_story(
    base_url: str,
    email: str,
    token: str,
    project_key: str,
    epic_key: str,
    summary: str,
    description: str,
    labels,
):
    # exact summary match
    jql = f'project = "{project_key}" AND summary ~ "\\"{summary}\\""'
    res = jira_search(base_url, email, token, jql, fields=["key", "summary"], max_results=10)
    for it in res.get("issues", []):
        if it.get("fields", {}).get("summary") == summary:
            return it["key"], False

    fields = {
        "project": {"key": project_key},
        "issuetype": {"name": "Story"},
        "summary": summary,
        "description": adf(description),
        "labels": labels,
        "parent": {"key": epic_key},
    }

    url = f"{base_url}/rest/api/3/issue"

    # retry on transient timeouts
    last_err = None
    for attempt in range(1, 4):
        try:
            status, out = jira_req("POST", url, email, token, {"fields": fields}, timeout=60)
            if status in (200, 201):
                return out["key"], True
            last_err = RuntimeError(out)
        except TimeoutError as e:
            last_err = e
        except Exception as e:
            last_err = e

    raise last_err or RuntimeError("Unknown Jira error")


def main():
    load_env("/home/bot/.moltbot/secrets/jira.env")
    base_url = os.environ["JIRA_BASE_URL"]
    email = os.environ["JIRA_EMAIL"]
    token = os.environ["JIRA_API_TOKEN"]
    project_key = os.environ.get("JIRA_PROJECT", "KAN")

    roadmap = {
        # Web UI
        "KAN-32": [
            (
                "UI: Requirements submission page",
                "Build UI to submit new project requirements; validate input; POST /api/projects.",
                ["agent_bus", "ui", "frontend"],
            ),
            (
                "UI: Project/job list + status page",
                "List jobs/projects with current stage/status; poll or websocket updates.",
                ["agent_bus", "ui", "frontend"],
            ),
            (
                "UI: PRD viewer + memory hits",
                "Display PRD markdown and memory hits; link to artifacts.",
                ["agent_bus", "ui", "frontend"],
            ),
            (
                "UI: HITL approval actions",
                "Add approve/request_changes controls; call endpoints; show audit trail.",
                ["agent_bus", "ui", "frontend", "hitl"],
            ),
            (
                "UI: Plan viewer",
                "Display plan artifact (milestones/tasks/dependencies) after approval.",
                ["agent_bus", "ui", "frontend"],
            ),
            (
                "UI: UX polish + basic error states",
                "Loading states, retries, empty/error handling, copy-to-clipboard.",
                ["agent_bus", "ui", "frontend", "devex"],
            ),
        ],
        # Workflow expansion
        "KAN-33": [
            (
                "Workflow: add Architecture stage + agent stub",
                "Add WorkflowStage + routing + minimal agent output artifact.",
                ["agent_bus", "workflow", "agents"],
            ),
            (
                "Workflow: add UI/UX stage + agent stub",
                "Add UI/UX design stage, artifact storage, and wiring.",
                ["agent_bus", "workflow", "agents"],
            ),
            (
                "Workflow: add Dev stage (TDD loop) + agent stub",
                "Add developer agent stage; produce code artifacts/tests.",
                ["agent_bus", "workflow", "agents", "dev"],
            ),
            (
                "Workflow: add QA stage + agent stub",
                "Add QA agent stage; run tests/playwright hooks; store report artifact.",
                ["agent_bus", "workflow", "agents", "qa"],
            ),
            (
                "Workflow: add Security review stage + agent stub",
                "Add security agent stage; produce findings artifact.",
                ["agent_bus", "workflow", "agents", "security"],
            ),
            (
                "Workflow: add Docs + Support stages + agent stubs",
                "Add technical writer + support engineer stages; artifacts.",
                ["agent_bus", "workflow", "agents", "docs"],
            ),
            (
                "Workflow: finalize end-to-end stage graph + transitions",
                "Define dependencies, approvals, and completion semantics.",
                ["agent_bus", "workflow"],
            ),
        ],
        # Skills system
        "KAN-34": [
            (
                "Skills: registry format + loader hardening",
                "Define skill schema + validation; improve load errors and caching.",
                ["agent_bus", "skills"],
            ),
            (
                "Skills: install command (git clone + register)",
                "Add CLI/script to install a skill from a git URL; record version.",
                ["agent_bus", "skills", "devex"],
            ),
            (
                "Skills: per-agent allowlist + capability mapping",
                "Control which agents can load which skills; map stage→skill.",
                ["agent_bus", "skills", "security"],
            ),
            (
                "Skills: add example skill + tests",
                "Include a minimal example skill in repo + tests for loading.",
                ["agent_bus", "skills", "tests"],
            ),
        ],
        # Memory system v2
        "KAN-35": [
            (
                "Memory: unify store interface + backends",
                "Formalize interface; keep TF-IDF as default backend.",
                ["agent_bus", "memory"],
            ),
            (
                "Memory: optional embeddings backend (pgvector or chroma)",
                "Add pluggable embeddings backend behind feature flag.",
                ["agent_bus", "memory", "embeddings"],
            ),
            (
                "Memory: retention + pattern types",
                "Define pattern_type taxonomy and retention policies; migrations if needed.",
                ["agent_bus", "memory"],
            ),
            (
                "Memory: evaluation harness",
                "Add deterministic eval set for retrieval quality + regression test.",
                ["agent_bus", "memory", "tests"],
            ),
        ],
        # Deployment & scaling
        "KAN-36": [
            (
                "Infra: split services (api/worker/orchestrator)",
                "Compose + docs for running separate services in prod.",
                ["agent_bus", "infra"],
            ),
            (
                "Infra: config/secrets strategy",
                "Env var schema, example files, secret injection guidance.",
                ["agent_bus", "infra", "security"],
            ),
            (
                "Infra: k8s manifests (dev)",
                "Basic k8s manifests for postgres/redis/api/worker.",
                ["agent_bus", "infra", "k8s"],
            ),
            (
                "Infra: helm chart (optional)",
                "Helm chart for configurable deploy.",
                ["agent_bus", "infra", "k8s"],
            ),
        ],
        # GPU routing
        "KAN-37": [
            (
                "GPU: add gpu worker queue + compose service",
                "Add agent_bus:tasks:gpu queue + gpu worker service (no actual GPU required).",
                ["agent_bus", "gpu", "routing"],
            ),
            (
                "GPU: improve ML workload detection",
                "Refine keyword detection; add tests + config overrides.",
                ["agent_bus", "gpu", "routing", "tests"],
            ),
            (
                "GPU: k8s gpu worker deployment (placeholder)",
                "Manifest for gpu worker with nodeSelector/tolerations.",
                ["agent_bus", "gpu", "k8s"],
            ),
        ],
        # Observability
        "KAN-38": [
            (
                "Obs: structured logging (json) for api/worker",
                "Standardize log fields: job_id, task_id, stage, latency.",
                ["agent_bus", "observability"],
            ),
            (
                "Obs: job/task event stream endpoint",
                "Expose recent agent_events/job timeline via API.",
                ["agent_bus", "observability", "api"],
            ),
            (
                "Obs: metrics endpoint (basic)",
                "Add /metrics (Prometheus) or simple counters for jobs/tasks.",
                ["agent_bus", "observability", "metrics"],
            ),
        ],
        # Security/auth
        "KAN-39": [
            (
                "Security: auth middleware for API",
                "Add token/session auth for API endpoints; protect approve endpoints.",
                ["agent_bus", "security", "auth"],
            ),
            (
                "Security: RBAC for HITL actions",
                "Only authorized users can approve/request changes.",
                ["agent_bus", "security", "auth", "hitl"],
            ),
            (
                "Security: secrets handling guidelines",
                "Docs + prevent secrets in repo; pre-commit checks.",
                ["agent_bus", "security", "devex"],
            ),
        ],
        # CI/CD hardening
        "KAN-40": [
            (
                "CI: add lint/format (ruff/black) + checks",
                "Add linting/formatting and enforce in CI.",
                ["agent_bus", "ci"],
            ),
            (
                "CI: container build cache improvements",
                "Enable build cache to speed up CI runs.",
                ["agent_bus", "ci", "devex"],
            ),
            (
                "CI: branch protection rules",
                "Require CI checks for main merges.",
                ["agent_bus", "ci", "governance"],
            ),
            (
                "CD: release tagging + deployment stub",
                "Add release workflow + placeholder deploy job.",
                ["agent_bus", "cd"],
            ),
        ],
    }

    created = {}
    existing = {}

    for epic_key, stories in roadmap.items():
        for title, desc, labels in stories:
            # Prefix summaries with epic short name for readability
            summary = f"{title}"
            key, was_created = ensure_story(
                base_url,
                email,
                token,
                project_key=project_key,
                epic_key=epic_key,
                summary=summary,
                description=desc,
                labels=labels + ["roadmap", f"epic:{epic_key}"],
            )
            (created if was_created else existing).setdefault(epic_key, []).append(key)

    print(json.dumps({"created": created, "existing": existing}, indent=2))


if __name__ == "__main__":
    main()
