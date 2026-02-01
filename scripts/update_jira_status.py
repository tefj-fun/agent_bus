#!/usr/bin/env python3
"""Update Jira issue status."""

import os
import json
import base64
import sys
from pathlib import Path
from urllib import request

def load_env_file(path: str):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        if '=' not in line or line.startswith('#'):
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_env_file('/home/bot/.moltbot/secrets/jira.env')

JIRA_BASE = os.getenv('JIRA_BASE_URL', 'https://kanbas.atlassian.net')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_TOKEN = os.getenv('JIRA_API_TOKEN')

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
            print(f"Error: {e.read().decode('utf-8')}")
        raise

def transition_issue(issue_key: str, transition_name: str):
    """Transition issue to new status."""
    # Get available transitions
    status, transitions = jira_req('GET', f'/rest/api/3/issue/{issue_key}/transitions')
    
    # Find transition ID
    transition_id = None
    for t in transitions['transitions']:
        if t['name'].lower() == transition_name.lower():
            transition_id = t['id']
            break
    
    if not transition_id:
        print(f"Available transitions for {issue_key}:")
        for t in transitions['transitions']:
            print(f"  - {t['name']} (id: {t['id']})")
        raise ValueError(f"Transition '{transition_name}' not found")
    
    # Perform transition
    payload = {"transition": {"id": transition_id}}
    status, _ = jira_req('POST', f'/rest/api/3/issue/{issue_key}/transitions', payload)
    
    if status in (200, 204):
        print(f"✓ Transitioned {issue_key} to {transition_name}")
        return True
    else:
        print(f"✗ Failed to transition {issue_key}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <issue_key> <status>")
        print(f"Example: {sys.argv[0]} KAN-86 Done")
        sys.exit(1)
    
    issue_key = sys.argv[1]
    status_name = sys.argv[2]
    
    transition_issue(issue_key, status_name)
