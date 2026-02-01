"""Integration test for QA workflow stage - E2E API test."""
import pytest

import os
import time
import uuid
import urllib.request
import json


# When running under `docker compose run api`, the API is reachable as http://api:8000
BASE_URL = os.getenv("BASE_URL", "http://api:8000").rstrip("/")


def http(method: str, url: str, payload=None, timeout=10):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, json.loads(body or "{}")


def wait_for(job_id: str, predicate, timeout_s: float = 60.0, poll_s: float = 1.0):
    start = time.time()
    last = None
    while time.time() - start < timeout_s:
        status, last = http("GET", f"{BASE_URL}/api/projects/{job_id}")
        assert status == 200
        if predicate(last):
            return last
        time.sleep(poll_s)
    raise AssertionError(f"Timed out waiting for condition. last={last}")


@pytest.mark.slow
def test_qa_stage_in_workflow():
    """Integration test: verify QA stage executes after development.

    Assumes stack is running locally (docker compose) and LLM_MODE=mock in CI.
    """
    project_id = f"qa_it_{uuid.uuid4().hex[:10]}"

    status, created = http(
        "POST",
        f"{BASE_URL}/api/projects/",
        payload={
            "project_id": project_id,
            "requirements": "PRD for a simple todo app with authentication.",
        },
        timeout=10,
    )
    assert status == 200
    job_id = created["job_id"]

    # Wait for PRD stage to complete
    job = wait_for(
        job_id,
        lambda j: j.get("workflow_stage") == "waiting_for_approval",
        timeout_s=120,
    )
    assert job.get("status") in {"waiting_for_approval", "in_progress", "orchestrating", "queued", "approved"}

    # Approve
    status, _ = http(
        "POST",
        f"{BASE_URL}/api/projects/{job_id}/approve",
        payload={"notes": "QA integration test"},
        timeout=10,
    )
    assert status == 200

    # Wait for completion
    job = wait_for(
        job_id,
        lambda j: j.get("status") == "completed" or j.get("workflow_stage") == "completed",
        timeout_s=240,
    )
    assert job.get("status") == "completed"

    # Development artifact exists
    _, dev = http("GET", f"{BASE_URL}/api/projects/{job_id}/development", timeout=10)
    assert dev.get("content") or dev.get("output_data")

    # QA artifact exists
    _, qa = http("GET", f"{BASE_URL}/api/projects/{job_id}/qa", timeout=10)
    assert qa.get("content") or qa.get("output_data")
    
    # Verify QA artifact contains expected structure
    qa_content = qa.get("content")
    if qa_content:
        if isinstance(qa_content, str):
            qa_data = json.loads(qa_content)
        else:
            qa_data = qa_content
        
        # Verify QA strategy structure
        assert "qa_strategy" in qa_data or "test_plans" in qa_data, "QA artifact should contain qa_strategy or test_plans"
