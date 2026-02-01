#!/usr/bin/env python3
"""Check KAN-36 status and subtasks in Jira."""
import os
from jira import JIRA

# Jira configuration
JIRA_SERVER = "https://kanbas.atlassian.net"
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "hello@tefj.fun")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

if not JIRA_API_TOKEN:
    print("ERROR: JIRA_API_TOKEN not set")
    exit(1)

# Connect to Jira
jira = JIRA(server=JIRA_SERVER, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))

# Fetch KAN-36
issue = jira.issue('KAN-36')

print(f"Issue: {issue.key}")
print(f"Summary: {issue.fields.summary}")
print(f"Status: {issue.fields.status.name}")
print(f"Type: {issue.fields.issuetype.name}")

# Check for subtasks
subtasks = getattr(issue.fields, 'subtasks', [])
print(f"\nSubtasks: {len(subtasks)}")

if subtasks:
    for st in subtasks:
        print(f"  - {st.key}: {st.fields.summary} ({st.fields.status.name})")
else:
    print("  No subtasks found - need to create them")
