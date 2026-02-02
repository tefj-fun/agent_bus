"""UI PRD + memory hits viewer."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ...infrastructure.postgres_client import postgres_client
from ...config import settings
from ...storage.artifact_store import get_artifact_store, FileArtifactStore

router = APIRouter()


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@router.get("/prd/{job_id}", response_class=HTMLResponse)
async def prd_view(job_id: str):
    """Render PRD content and memory hits for a job."""
    prd_content = None
    hits = []
    workflow_stage = None

    # Get job status to determine if actions should be shown
    pool = await postgres_client.get_pool()
    async with pool.acquire() as conn:
        job_row = await conn.fetchrow(
            "SELECT workflow_stage FROM jobs WHERE id = $1",
            job_id,
        )
        workflow_stage = job_row["workflow_stage"] if job_row else None

    # Try file storage first if configured
    if settings.artifact_storage_backend == "file":
        try:
            store = get_artifact_store()
            if isinstance(store, FileArtifactStore):
                artifact = await store.get_latest_by_type(job_id, "prd")
                if artifact:
                    prd_content = artifact.get("content")
                    hits = artifact.get("metadata", {}).get("memory_hits", [])
        except RuntimeError:
            pass  # Artifact store not initialized, fall back to DB

    # Fall back to PostgreSQL if no file content found
    if not prd_content:
        pool = await postgres_client.get_pool()
        async with pool.acquire() as conn:
            prd_row = await conn.fetchrow(
                """
                SELECT content, metadata
                FROM artifacts
                WHERE job_id = $1 AND type = 'prd'
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                job_id,
            )

            # fallback to tasks output_data
            if not prd_row:
                prd_task = await conn.fetchrow(
                    """
                    SELECT output_data->>'prd_content' AS prd_content,
                           output_data->'memory_hits' AS memory_hits
                    FROM tasks
                    WHERE job_id = $1 AND task_type='prd_generation'
                    ORDER BY completed_at DESC, created_at DESC
                    LIMIT 1
                    """,
                    job_id,
                )
                prd_content = (prd_task or {}).get("prd_content") if prd_task else None
                hits = (prd_task or {}).get("memory_hits") if prd_task else []
            else:
                prd_content = prd_row.get("content")
                meta = prd_row.get("metadata") or {}
                hits = meta.get("memory_hits") if isinstance(meta, dict) else []

    prd_text = _escape(prd_content or "(no PRD found)")

    items = []
    if isinstance(hits, list):
        for h in hits:
            if isinstance(h, dict):
                items.append(
                    f"<li><code>{_escape(str(h.get('id')))}</code> score={_escape(str(h.get('score')))}</li>"
                )
            else:
                items.append(f"<li>{_escape(str(h))}</li>")
    hits_html = "\n".join(items) if items else "<li>(none)</li>"

    # Only show actions if job is waiting for approval
    if workflow_stage == "Waiting_Approval":
        actions_html = f"""
    <div class=\"card\" style=\"margin-top:12px\">
      <h3>Actions</h3>
      <form method=\"post\" action=\"/ui/prd/{job_id}/approve\">
        <label>Approval notes</label><br/>
        <textarea name=\"notes\" style=\"width:100%;min-height:80px\" placeholder=\"Optional notes\"></textarea>
        <div style=\"margin-top:10px;display:flex;gap:10px\">
          <button type=\"submit\" style=\"padding:10px 14px;border:0;border-radius:8px;background:#16a34a;color:white;cursor:pointer\">Approve</button>
        </div>
      </form>
      <form method=\"post\" action=\"/ui/prd/{job_id}/request_changes\" style=\"margin-top:10px\">
        <label>Change request notes</label><br/>
        <textarea name=\"notes\" style=\"width:100%;min-height:80px\" placeholder=\"What needs to change?\"></textarea>
        <div style=\"margin-top:10px;display:flex;gap:10px\">
          <button type=\"submit\" style=\"padding:10px 14px;border:0;border-radius:8px;background:#b45309;color:white;cursor:pointer\">Request changes</button>
        </div>
      </form>
    </div>"""
    else:
        stage_display = _escape(workflow_stage or "unknown")
        actions_html = f"""
    <div class=\"card\" style=\"margin-top:12px;background:#f9fafb\">
      <p style=\"margin:0;color:#6b7280\">Actions not available. Current stage: <strong>{stage_display}</strong></p>
    </div>"""

    return f"""
<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>PRD {job_id}</title>
    <style>
      body {{ font-family: ui-sans-serif, system-ui; margin: 24px; }}
      a {{ color: #2563eb; }}
      pre {{ white-space: pre-wrap; background:#f3f4f6; padding: 12px; border-radius: 10px; max-width: 1100px; }}
      code {{ background:#f3f4f6; padding:2px 6px; border-radius:6px; }}
      .row {{ display:flex; gap: 16px; align-items: center; }}
      .card {{ border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; max-width: 1100px; }}
    </style>
  </head>
  <body>
    <div class=\"row\">
      <h2 style=\"margin:0\">PRD Viewer</h2>
      <a href=\"/ui/jobs\">Jobs</a>
      <a href=\"/ui/plan/{job_id}\">Plan</a>
      <a href=\"/ui/\">Create</a>
      <a href=\"/api/projects/{job_id}\">API status</a>
    </div>

    <p><strong>job_id:</strong> <code>{job_id}</code></p>

    <h3>PRD content</h3>
    <pre>{prd_text}</pre>

    <div class=\"card\" style=\"margin-top:12px\">
      <h3>Memory hits</h3>
      <ul>
        {hits_html}
      </ul>
    </div>

    {actions_html}
  </body>
</html>
"""
