#!/usr/bin/env python3
"""Create/update Jira issues for agent_bus TODOs.

Reads Jira creds from /home/bot/.moltbot/secrets/jira.env (or env vars) and
creates one Epic + Tasks under project KAN.

Idempotent-ish: searches by exact summary and reuses existing issues.
"""

import os
import re
import sys
import json
import base64
from pathlib import Path
from urllib import request, parse


def load_env_file(path: str):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)


def jira_req(method: str, url: str, email: str, token: str, payload=None):
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(f'{email}:{token}'.encode()).decode(),
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
    req = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode('utf-8')
        return resp.status, json.loads(body) if body else {}


def jira_search(base_url: str, email: str, token: str, jql: str, fields=None, max_results=10):
    # Jira Cloud: /rest/api/3/search is returning 410 Gone; use /search/jql.
    url = f"{base_url}/rest/api/3/search/jql"
    payload = {
        'jql': jql,
        'maxResults': max_results,
    }
    if fields:
        payload['fields'] = fields
    _, out = jira_req('POST', url, email, token, payload)
    return out


def ensure_issue(base_url: str, email: str, token: str, project_key: str, issue_type: str, summary: str, description_adf: dict, labels=None, parent_key=None):
    # Find existing by exact summary
    jql = f'project = "{project_key}" AND summary ~ "\\"{summary}\\""'
    res = jira_search(base_url, email, token, jql, fields=['key','summary'], max_results=5)
    issues = res.get('issues', [])
    for it in issues:
        if it.get('fields', {}).get('summary') == summary:
            return it['key'], False

    fields = {
        'project': {'key': project_key},
        'issuetype': {'name': issue_type},
        'summary': summary,
        'description': description_adf,
    }
    if labels:
        fields['labels'] = labels
    # Use Epic Link / parent only if supported; safest is to omit unless we know the schema.
    if parent_key:
        # Jira Cloud: sub-task uses "parent". For tasks under epic you need a custom field.
        # We'll store the epic key in labels for now.
        fields.setdefault('labels', []).append(f'epic:{parent_key}')

    url = f"{base_url}/rest/api/3/issue"
    status, out = jira_req('POST', url, email, token, {'fields': fields})
    if status not in (200, 201):
        raise RuntimeError(out)
    return out['key'], True


def adf_doc(text: str) -> dict:
    # Minimal Atlassian Document Format (ADF)
    return {
        'type': 'doc',
        'version': 1,
        'content': [
            {
                'type': 'paragraph',
                'content': [{'type': 'text', 'text': text}],
            }
        ],
    }


def main():
    load_env_file('/home/bot/.moltbot/secrets/jira.env')

    base_url = os.environ.get('JIRA_BASE_URL')
    email = os.environ.get('JIRA_EMAIL')
    token = os.environ.get('JIRA_API_TOKEN')
    if not (base_url and email and token):
        print('Missing Jira env vars. Need JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN', file=sys.stderr)
        return 2

    project_key = os.environ.get('JIRA_PROJECT', 'KAN')

    # Verify auth quickly
    me_url = f"{base_url}/rest/api/3/myself"
    jira_req('GET', me_url, email, token)

    epic_summary = 'agent_bus: Phase 5 integration & QA'
    epic_key, epic_created = ensure_issue(
        base_url, email, token,
        project_key=project_key,
        issue_type='Epic',
        summary=epic_summary,
        description_adf=adf_doc('Backlog for Phase 5: integration tests, durability, CI hardening.'),
        labels=['agent_bus', 'phase5', 'qa'],
    )

    tasks = [
        (
            'agent_bus: Fix memory_hits API contract (return JSON list)',
            "Change /api/projects/{job_id}/memory_hits to return memory_hits as an actual JSON array; add tests; then simplify smoke script.",
            ['agent_bus','phase5','api','qa']
        ),
        (
            'agent_bus: Add integration tests for async + HITL flow',
            'Add pytest integration tests covering create → PRD → waiting_for_approval → approve → plan → completed; assert artifacts exist; add failure-mode test.',
            ['agent_bus','phase5','qa','tests']
        ),
        (
            'agent_bus: Orchestration resiliency (survive API restarts)',
            'Move orchestration loop out of FastAPI process (dedicated orchestrator service) so jobs continue across API restarts; add restart-resilience integration test.',
            ['agent_bus','phase5','orchestration','reliability']
        ),
        (
            'agent_bus: CI cleanup (eliminate git exit code 128 annotation)',
            'Investigate and remove the noisy GitHub Actions annotation about git exit code 128 so CI output is clean.',
            ['agent_bus','ci','devex']
        ),
        (
            'agent_bus: LLM provider switch (Codex/Claude)',
            'Add LLM_PROVIDER config and implement OpenAI (Codex) + Anthropic (Claude) switch; add tests; ensure CI smoke still passes.',
            ['agent_bus','phase5','llm']
        ),
    ]

    created = []
    existing = []
    for summary, desc, labels in tasks:
        key, was_created = ensure_issue(
            base_url, email, token,
            project_key=project_key,
            issue_type='Task',
            summary=summary,
            description_adf=adf_doc(desc),
            labels=labels + [f'epic:{epic_key}'],
            parent_key=epic_key,
        )
        (created if was_created else existing).append(key)

    print(json.dumps({
        'epic': epic_key,
        'created': created,
        'existing': existing,
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
