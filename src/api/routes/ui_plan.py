"""UI plan viewer."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ...infrastructure.postgres_client import postgres_client

router = APIRouter()


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


@router.get("/plan/{job_id}", response_class=HTMLResponse)
async def plan_view(job_id: str):
    pool = await postgres_client.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT content, metadata, updated_at, created_at
            FROM artifacts
            WHERE job_id = $1 AND type = 'plan'
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
            """,
            job_id,
        )

    if not row:
        body = "<p>(no plan artifact found yet)</p>"
    else:
        content = row.get("content") or ""
        body = f"<pre>{_escape(content)}</pre>"

    return f"""
<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Plan {job_id}</title>
    <style>
      body {{ font-family: ui-sans-serif, system-ui; margin: 24px; }}
      a {{ color: #2563eb; }}
      pre {{ white-space: pre-wrap; background:#f3f4f6; padding: 12px; border-radius: 10px; max-width: 1100px; }}
      code {{ background:#f3f4f6; padding:2px 6px; border-radius:6px; }}
      .row {{ display:flex; gap: 16px; align-items: center; }}
    </style>
  </head>
  <body>
    <div class=\"row\">
      <h2 style=\"margin:0\">Plan Viewer</h2>
      <a href=\"/ui/jobs\">Jobs</a>
      <a href=\"/ui/prd/{job_id}\">PRD</a>
      <a href=\"/ui/\">Create</a>
      <a href=\"/api/projects/{job_id}\">API status</a>
    </div>

    <p><strong>job_id:</strong> <code>{job_id}</code></p>
    {body}
  </body>
</html>
"""
