"""UI PRD + memory hits viewer."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ...infrastructure.postgres_client import postgres_client

router = APIRouter()


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@router.get("/prd/{job_id}", response_class=HTMLResponse)
async def prd_view(job_id: str):
    """Render PRD content and memory hits for a job."""
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

    <div class=\"card\">
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
    </div>

    <div class=\"card\" style=\"margin-top:12px\">
      <h3>Memory hits</h3>
      <ul>
        {hits_html}
      </ul>
    </div>

    <h3>PRD content</h3>
    <pre>{prd_text}</pre>
  </body>
</html>
"""
