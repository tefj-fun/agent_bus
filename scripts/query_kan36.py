#!/usr/bin/env python3
"""Query KAN-36 and its subtasks from Jira."""

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

def jira_get(path: str):
    url = f"{JIRA_BASE}{path}"
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic ' + base64.b64encode(f'{JIRA_EMAIL}:{JIRA_TOKEN}'.encode()).decode(),
    }
    req = request.Request(url, headers=headers, method='GET')
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

# Get KAN-36 details
issue = jira_get('/rest/api/3/issue/KAN-36')

print(f"Key: {issue['key']}")
print(f"Summary: {issue['fields']['summary']}")
print(f"Status: {issue['fields']['status']['name']}")
print(f"Type: {issue['fields']['issuetype']['name']}")

# Get subtasks
subtasks = issue['fields'].get('subtasks', [])
print(f"\nSubtasks: {len(subtasks)}")
for st in subtasks:
    print(f"  - {st['key']}: {st['fields']['summary']} ({st['fields']['status']['name']})")

if not subtasks:
    print("\nNo subtasks found. Need to create deployment subtasks.")
