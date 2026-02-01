import os
import time
import uuid

import urllib.request
import json


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


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


def test_async_hitl_flow_end_to_end():
    """Integration test: create -> waiting_for_approval -> approve -> completed.

    Assumes stack is running locally (docker compose) and LLM_MODE=mock in CI.
    """
    project_id = f"it_{uuid.uuid4().hex[:10]}"

    status, created = http(
        "POST",
        f"{BASE_URL}/api/projects/",
        payload={
            "project_id": project_id,
            "requirements": "PRD for a lightweight bug tracker with tags, search, and SLAs.",
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

    # PRD exists
    _, prd = http("GET", f"{BASE_URL}/api/projects/{job_id}/prd", timeout=10)
    assert prd.get("content")

    # Approve
    status, _ = http(
        "POST",
        f"{BASE_URL}/api/projects/{job_id}/approve",
        payload={"notes": "integration test"},
        timeout=10,
    )
    assert status == 200

    # Completed
    job = wait_for(
        job_id,
        lambda j: j.get("status") == "completed" or j.get("workflow_stage") == "completed",
        timeout_s=180,
    )
    assert job.get("status") == "completed"
