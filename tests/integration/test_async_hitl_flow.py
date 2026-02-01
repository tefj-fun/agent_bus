import os
import time
import uuid

import requests


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


def wait_for(job_id: str, predicate, timeout_s: float = 60.0, poll_s: float = 1.0):
    start = time.time()
    last = None
    while time.time() - start < timeout_s:
        r = requests.get(f"{BASE_URL}/api/projects/{job_id}", timeout=10)
        r.raise_for_status()
        last = r.json()
        if predicate(last):
            return last
        time.sleep(poll_s)
    raise AssertionError(f"Timed out waiting for condition. last={last}")


def test_async_hitl_flow_end_to_end():
    """Integration test: create -> waiting_for_approval -> approve -> completed.

    Assumes stack is running locally (docker compose) and LLM_MODE=mock in CI.
    """
    project_id = f"it_{uuid.uuid4().hex[:10]}"

    r = requests.post(
        f"{BASE_URL}/api/projects/",
        json={
            "project_id": project_id,
            "requirements": "PRD for a lightweight bug tracker with tags, search, and SLAs.",
        },
        timeout=10,
    )
    r.raise_for_status()
    created = r.json()
    job_id = created["job_id"]

    # Wait for PRD stage to complete
    job = wait_for(
        job_id,
        lambda j: j.get("workflow_stage") == "waiting_for_approval",
        timeout_s=120,
    )
    assert job.get("status") in {"waiting_for_approval", "in_progress", "orchestrating", "queued", "approved"}

    # PRD exists
    prd = requests.get(f"{BASE_URL}/api/projects/{job_id}/prd", timeout=10).json()
    assert prd.get("content")

    # Approve
    r = requests.post(
        f"{BASE_URL}/api/projects/{job_id}/approve",
        json={"notes": "integration test"},
        timeout=10,
    )
    r.raise_for_status()

    # Completed
    job = wait_for(
        job_id,
        lambda j: j.get("status") == "completed" or j.get("workflow_stage") == "completed",
        timeout_s=180,
    )
    assert job.get("status") == "completed"
