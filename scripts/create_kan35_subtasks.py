#!/usr/bin/env python3
"""Create subtasks for KAN-35 (Memory system v2)."""

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
    """Convert plain text to Atlassian Document Format."""
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


def ensure_task(
    base_url: str,
    email: str,
    token: str,
    project_key: str,
    parent_key: str,
    summary: str,
    description: str,
):
    """Create task if it doesn't exist (checks by exact summary match)."""
    # Search for existing task
    jql = f'project = "{project_key}" AND summary ~ "\\"{summary}\\""'
    res = jira_search(base_url, email, token, jql, fields=["key", "summary"], max_results=10)
    for it in res.get("issues", []):
        if it.get("fields", {}).get("summary") == summary:
            return it["key"], False

    # Create new task
    fields = {
        "project": {"key": project_key},
        "summary": summary,
        "description": adf(description),
        "issuetype": {"name": "Task"},
        "parent": {"key": parent_key},
    }
    payload = {"fields": fields}
    url = f"{base_url}/rest/api/3/issue"
    _, created = jira_req("POST", url, email, token, payload, timeout=60)
    return created["key"], True


def main():
    load_env("/home/bot/.moltbot/secrets/jira.env")
    base_url = (os.environ.get("JIRA_URL") or os.environ.get("JIRA_BASE_URL", "")).rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")

    if not all([base_url, email, token]):
        print("ERROR: Missing Jira credentials (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)")
        return 1

    project_key = "KAN"
    parent_key = "KAN-35"

    subtasks = [
        {
            "summary": "Memory v2: ChromaDB integration and schema",
            "description": """Set up ChromaDB as vector database backend for Memory system v2.

Tasks:
- Add chromadb dependency to pyproject.toml
- Create ChromaDBStore class in src/memory/chroma_store.py
- Implement connection management and health checks
- Add configuration for ChromaDB (local vs server mode)
- Create migration path from existing TF-IDF store
- Add basic unit tests

Acceptance:
- ChromaDB can initialize and connect successfully
- Health check endpoint works
- Tests pass""",
        },
        {
            "summary": "Memory v2: Vector embeddings with sentence-transformers",
            "description": """Implement vector embedding generation for semantic search.

Tasks:
- Add sentence-transformers dependency
- Create EmbeddingGenerator class
- Implement document chunking for large texts
- Add embedding caching to avoid recomputation
- Update ChromaDBStore to use embeddings
- Add unit tests for embedding generation

Acceptance:
- Documents are automatically embedded on storage
- Query uses semantic similarity (not just keyword matching)
- Embedding generation is cached and efficient
- Tests pass""",
        },
        {
            "summary": "Memory v2: Pattern storage and retrieval",
            "description": """Build pattern recognition system for reusable components.

Tasks:
- Define pattern schema (PRDs, architectures, code snippets, etc.)
- Implement pattern storage with metadata tagging
- Add pattern retrieval with filtering (by type, success_score, etc.)
- Update MemoryAgent to support pattern operations
- Add success scoring and usage tracking
- Create API endpoints for pattern management
- Add comprehensive tests

Acceptance:
- Patterns can be stored with rich metadata
- Pattern retrieval supports filtering and ranking
- Usage tracking increments on retrieval
- API endpoints work correctly
- Tests pass""",
        },
        {
            "summary": "Memory v2: Template suggestion system",
            "description": """Implement intelligent template suggestion based on similarity.

Tasks:
- Create template matching algorithm
- Implement suggestion ranking (similarity + success_score)
- Add template suggestion to PRDAgent workflow
- Update orchestration to query memory before PRD generation
- Create template seeding utility
- Add integration tests for template workflow

Acceptance:
- Similar past projects are found automatically
- Templates are ranked by relevance and quality
- PRDAgent receives memory hits before generation
- Memory hits are exposed via API
- Integration test verifies end-to-end flow
- Tests pass""",
        },
        {
            "summary": "Memory v2: Seed templates and documentation",
            "description": """Populate memory with initial templates and finalize documentation.

Tasks:
- Create seed templates for common project types (web app, API, ML pipeline, etc.)
- Write migration script to populate initial templates
- Update docs/MEMORY_SYSTEM.md with v2 architecture
- Add usage examples for developers
- Create admin CLI commands for memory management
- Update README with memory system overview

Acceptance:
- At least 5 high-quality seed templates exist
- Migration script successfully populates templates
- Documentation is complete and clear
- CLI commands work (list, query, add, delete patterns)
- README updated""",
        },
    ]

    created = []
    for task in subtasks:
        key, is_new = ensure_task(
            base_url, email, token, project_key, parent_key, task["summary"], task["description"]
        )
        status = "CREATED" if is_new else "EXISTS"
        created.append(key)
        print(f'[{status}] {key}: {task["summary"]}')

    print(f"\nAll subtasks for {parent_key}:")
    for key in created:
        print(f"  - {key}")

    return 0


if __name__ == "__main__":
    exit(main())
