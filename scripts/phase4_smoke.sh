#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}
PROJECT_ID=${PROJECT_ID:-phase4_async_smoke}
REQUIREMENTS=${REQUIREMENTS:-"PRD for a lightweight bug tracker with tags, search, and SLAs."}
POLL_SECS=${POLL_SECS:-2}
TIMEOUT_SECS=${TIMEOUT_SECS:-600}

python3 - <<'PY'
import os, json, time, urllib.request

base=os.environ.get('BASE_URL','http://localhost:8000').rstrip('/')
project_id=os.environ.get('PROJECT_ID','phase4_async_smoke')
requirements=os.environ.get('REQUIREMENTS','PRD for a lightweight bug tracker with tags, search, and SLAs.')
poll_secs=float(os.environ.get('POLL_SECS','2'))
timeout_secs=float(os.environ.get('TIMEOUT_SECS','600'))

def req(method, path, payload=None):
    url=f"{base}{path}"
    data=None
    headers={'Accept':'application/json'}
    if payload is not None:
        data=json.dumps(payload).encode('utf-8')
        headers['Content-Type']='application/json'
    r=urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=30) as resp:
        body=resp.read()
        return resp.status, json.loads(body.decode('utf-8') or '{}')

print(f"[phase4_smoke] BASE_URL={base}")

status, created = req('POST','/api/projects/', {'project_id': project_id, 'requirements': requirements})
assert status == 200, (status, created)
job_id = created.get('job_id')
assert job_id and job_id.startswith('job_'), created
print(f"[phase4_smoke] created job_id={job_id} status={created.get('status')}")

# Poll until waiting_for_approval
start=time.time()
stage=None
job=None
while True:
    if time.time()-start > timeout_secs:
        raise SystemExit(f"timeout waiting for waiting_for_approval (last stage={stage})")
    status, job = req('GET', f'/api/projects/{job_id}')
    assert status == 200, (status, job)
    stage = job.get('workflow_stage')
    if stage == 'waiting_for_approval':
        break
    if job.get('status') == 'failed' or stage == 'failed':
        raise SystemExit(f"job failed before approval: {job}")
    time.sleep(poll_secs)

print(f"[phase4_smoke] reached waiting_for_approval")

status, prd = req('GET', f'/api/projects/{job_id}/prd')
assert status == 200, (status, prd)
content = prd.get('content')
assert content and len(content) > 50, "PRD content missing/too short"
print(f"[phase4_smoke] prd ok (len={len(content)})")

status, hits = req('GET', f'/api/projects/{job_id}/memory_hits')
assert status == 200, (status, hits)
mh = hits.get('memory_hits')
# API may return memory_hits as a JSON-encoded string; normalize to list.
if isinstance(mh, str):
    try:
        mh = json.loads(mh)
    except Exception:
        pass
assert isinstance(mh, list), {'job_id': job_id, 'memory_hits': hits.get('memory_hits')}
print(f"[phase4_smoke] memory_hits ok (n={len(mh)})")

status, approved = req('POST', f'/api/projects/{job_id}/approve', {'notes':'Autonomous smoke approval'})
assert status == 200, (status, approved)
print(f"[phase4_smoke] approved")

# Poll until completed
start=time.time()
while True:
    if time.time()-start > timeout_secs:
        raise SystemExit(f"timeout waiting for completed")
    status, job = req('GET', f'/api/projects/{job_id}')
    assert status == 200, (status, job)
    stage = job.get('workflow_stage')
    if stage == 'completed' or job.get('status') == 'completed':
        break
    if job.get('status') == 'failed' or stage == 'failed':
        raise SystemExit(f"job failed after approval: {job}")
    time.sleep(poll_secs)

print(f"[phase4_smoke] completed")

print(json.dumps({
  'job_id': job_id,
  'final_status': job.get('status'),
  'final_stage': job.get('workflow_stage')
}, indent=2))
PY
