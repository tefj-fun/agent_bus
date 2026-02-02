"""Integration test for Security workflow stage - E2E API test."""

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
def test_security_stage_in_workflow():
    """Integration test: verify Security stage executes after QA.

    Assumes stack is running locally (docker compose) and LLM_MODE=mock in CI.
    """
    project_id = f"sec_it_{uuid.uuid4().hex[:10]}"

    status, created = http(
        "POST",
        f"{BASE_URL}/api/projects/",
        payload={
            "project_id": project_id,
            "requirements": "PRD for a web application with user authentication and payment processing.",
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
    assert job.get("status") in {
        "waiting_for_approval",
        "in_progress",
        "orchestrating",
        "queued",
        "approved",
    }

    # Approve
    status, _ = http(
        "POST",
        f"{BASE_URL}/api/projects/{job_id}/approve",
        payload={"notes": "Security integration test"},
        timeout=10,
    )
    assert status == 200

    # Wait for completion
    job = wait_for(
        job_id,
        lambda j: j.get("status") == "completed" or j.get("workflow_stage") == "completed",
        timeout_s=300,
    )
    assert job.get("status") == "completed"

    # QA artifact exists
    _, qa = http("GET", f"{BASE_URL}/api/projects/{job_id}/qa", timeout=10)
    assert qa.get("content") or qa.get("output_data")

    # Security artifact exists
    _, security = http("GET", f"{BASE_URL}/api/projects/{job_id}/security", timeout=10)
    assert security.get("content") or security.get("output_data")

    # Verify Security artifact contains expected structure
    security_content = security.get("content")
    if security_content:
        if isinstance(security_content, str):
            security_data = json.loads(security_content)
        else:
            security_data = security_content

        # Verify security audit structure
        assert (
            "security_audit" in security_data or "vulnerabilities" in security_data
        ), "Security artifact should contain security_audit or vulnerabilities"

        # Verify vulnerabilities exist
        if "vulnerabilities" in security_data:
            assert (
                len(security_data["vulnerabilities"]) > 0
            ), "Should have identified vulnerabilities"

            # Check first vulnerability has required fields
            vuln = security_data["vulnerabilities"][0]
            assert "vulnerability_id" in vuln
            assert "severity" in vuln
            assert "category" in vuln
            assert "recommendation" in vuln


@pytest.mark.slow
def test_security_api_endpoint():
    """Test the security endpoint returns 404 for non-existent job."""
    fake_job_id = f"fake_job_{uuid.uuid4().hex[:10]}"

    try:
        status, _ = http("GET", f"{BASE_URL}/api/projects/{fake_job_id}/security", timeout=10)
        # Should not reach here
        assert False, f"Expected 404, got {status}"
    except urllib.error.HTTPError as e:
        assert e.code == 404
