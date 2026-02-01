"""Minimal HTML UI routes.

Phase 1 UI: submit requirements and create a job.

This is intentionally simple (server-rendered HTML) to avoid adding a frontend build
pipeline until requirements stabilize.
"""

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from .projects import ProjectRequest, create_project

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home():
    return """
<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>agent_bus</title>
    <style>
      body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; margin: 24px; }
      .card { max-width: 760px; border: 1px solid #ddd; border-radius: 10px; padding: 18px; }
      label { display:block; margin-top: 12px; font-weight: 600; }
      input, textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px; font-size: 14px; }
      textarea { min-height: 160px; }
      button { margin-top: 14px; padding: 10px 14px; border: 0; border-radius: 8px; background: #111827; color: white; cursor: pointer; }
      .muted { color: #6b7280; font-size: 13px; margin-top: 6px; }
    </style>
  </head>
  <body>
    <h1>agent_bus</h1>
    <div class=\"card\">
      <form method=\"post\" action=\"/ui/create\">
        <label>Project ID</label>
        <input name=\"project_id\" placeholder=\"e.g. solomon_bug_tracker\" required />

        <label>Requirements</label>
        <textarea name=\"requirements\" placeholder=\"Describe what you want built...\" required></textarea>

        <button type=\"submit\">Create project</button>
        <div class=\"muted\">Creates a queued job and returns a job_id.</div>
      </form>
    </div>
  </body>
</html>
"""


@router.post("/create", response_class=HTMLResponse)
async def create(project_id: str = Form(...), requirements: str = Form(...)):
    try:
        req = ProjectRequest(project_id=project_id, requirements=requirements, metadata=None)
        resp = await create_project(req)
        job_id = resp.job_id

        return f"""
<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Created</title>
    <style>
      body {{ font-family: ui-sans-serif, system-ui; margin: 24px; }}
      a {{ color: #2563eb; }}
      code {{ background:#f3f4f6; padding:2px 6px; border-radius:6px; }}
      .ok {{ padding: 10px 12px; border-radius: 10px; background: #ecfdf5; border: 1px solid #a7f3d0; }}
    </style>
  </head>
  <body>
    <div class=\"ok\">
      <h2 style=\"margin:0 0 8px 0\">Created job</h2>
      <p><strong>job_id:</strong> <code>{job_id}</code></p>
      <p>
        <a href=\"/ui/\">Create another</a> ·
        <a href=\"/ui/jobs\">Jobs</a> ·
        <a href=\"/ui/prd/{job_id}\">PRD</a> ·
        <a href=\"/ui/plan/{job_id}\">Plan</a> ·
        <a href=\"/api/projects/{job_id}\">API status</a>
      </p>
    </div>
  </body>
</html>
"""

    except Exception as e:
        msg = str(e)
        return f"""
<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Error</title>
    <style>
      body {{ font-family: ui-sans-serif, system-ui; margin: 24px; }}
      .err {{ padding: 10px 12px; border-radius: 10px; background: #fef2f2; border: 1px solid #fecaca; }}
      pre {{ white-space: pre-wrap; }}
      a {{ color: #2563eb; }}
    </style>
  </head>
  <body>
    <div class=\"err\">
      <h2 style=\"margin:0 0 8px 0\">Create failed</h2>
      <pre>{msg}</pre>
      <p><a href=\"/ui/\">Back</a></p>
    </div>
  </body>
</html>
"""
