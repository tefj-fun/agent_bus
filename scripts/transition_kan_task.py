#!/usr/bin/env python3
"""Transition a KAN task to a specific status."""

import os
import sys
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


def get_transitions(base_url: str, email: str, token: str, issue_key: str):
    """Get available transitions for an issue."""
    url = f"{base_url}/rest/api/3/issue/{issue_key}/transitions"
    _, result = jira_req("GET", url, email, token)
    return result.get("transitions", [])


def transition_issue(base_url: str, email: str, token: str, issue_key: str, transition_name: str):
    """Transition issue to specified status."""
    # Get available transitions
    transitions = get_transitions(base_url, email, token, issue_key)

    # Find matching transition
    transition_id = None
    for t in transitions:
        if (
            t["name"].lower() == transition_name.lower()
            or t["to"]["name"].lower() == transition_name.lower()
        ):
            transition_id = t["id"]
            break

    if not transition_id:
        print(f'ERROR: Could not find transition to "{transition_name}"')
        print(f'Available transitions: {[t["name"] for t in transitions]}')
        return False

    # Execute transition
    url = f"{base_url}/rest/api/3/issue/{issue_key}/transitions"
    payload = {"transition": {"id": transition_id}}
    _, result = jira_req("POST", url, email, token, payload)
    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: transition_kan_task.py <ISSUE_KEY> <STATUS>")
        print('Example: transition_kan_task.py KAN-81 "In Progress"')
        return 1

    load_env("/home/bot/.moltbot/secrets/jira.env")
    base_url = (os.environ.get("JIRA_URL") or os.environ.get("JIRA_BASE_URL", "")).rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")

    if not all([base_url, email, token]):
        print("ERROR: Missing Jira credentials")
        return 1

    issue_key = sys.argv[1]
    status = sys.argv[2]

    if transition_issue(base_url, email, token, issue_key, status):
        print(f'✓ Transitioned {issue_key} to "{status}"')
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
