#!/usr/bin/env python3
"""Create KAN-36 deployment tasks in Jira."""

import os
import json
import base64
from pathlib import Path
from urllib import request

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

load_env_file('/home/bot/.moltbot/secrets/jira.env')

JIRA_BASE = os.getenv('JIRA_BASE_URL', 'https://kanbas.atlassian.net')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_TOKEN = os.getenv('JIRA_API_TOKEN')
PROJECT_KEY = 'KAN'

def jira_req(method: str, path: str, payload=None):
    url = f"{JIRA_BASE}{path}"
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(f'{JIRA_EMAIL}:{JIRA_TOKEN}'.encode()).decode(),
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
            return resp.status, json.loads(body) if body else {}
    except Exception as e:
        if hasattr(e, 'read'):
            error_body = e.read().decode('utf-8')
            print(f"Error response: {error_body}")
        raise

def create_task_in_epic(epic_key: str, summary: str):
    """Create a Task under the Epic as a child."""
    # Create task with parent field
    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": summary,
            "issuetype": {"name": "Task"},
            "parent": {"key": epic_key}
        }
    }
    
    status, result = jira_req('POST', '/rest/api/3/issue', payload)
    if status in (200, 201):
        return result['key']
    else:
        print(f"Error creating task: {status} - {result}")
        return None

# Define tasks for KAN-36 (Deployment & Scaling)
tasks = [
    "Docker: Optimize Dockerfile and multi-stage builds",
    "K8s: Create base manifests (deployments, services, ConfigMaps)",
    "K8s: Implement Helm charts for environment management",
    "K8s: GPU worker jobs and node affinity",
    "Observability: Add Prometheus metrics and basic monitoring"
]

print(f"Creating {len(tasks)} child tasks under epic KAN-36...")
created = []

for summary in tasks:
    print(f"\nCreating: {summary}")
    key = create_task_in_epic('KAN-36', summary)
    if key:
        print(f"  ✓ Created {key}")
        created.append(key)
    else:
        print(f"  ✗ Failed to create")

print(f"\n{'='*60}")
print(f"Summary: Created {len(created)}/{len(tasks)} tasks")
print(f"Created: {', '.join(created)}")

# Verify by querying KAN-36 again
if created:
    print(f"\n\nVerifying KAN-36 children...")
    _, kan36 = jira_req('GET', '/rest/api/3/issue/KAN-36')
    children = kan36.get('fields', {}).get('subtasks', [])
    print(f"KAN-36 now has {len(children)} children")
