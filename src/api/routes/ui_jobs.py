"""UI job list/status pages."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ...infrastructure.postgres_client import postgres_client

router = APIRouter()


@router.get("/jobs", response_class=HTMLResponse)
async def jobs_list(limit: int = 50):
    pool = await postgres_client.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, project_id, status, workflow_stage, created_at, updated_at
            FROM jobs
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )

    trs = []
    for r in rows:
        job_id = r["id"]
        trs.append(
            f"<tr>"
            f"<td><a href=\"/api/projects/{job_id}\">{job_id}</a></td>"
            f"<td>{r[project_id]}</td>"
            f"<td>{r[status]}</td>"
            f"<td>{r[workflow_stage]}</td>"
            f"<td>{r[updated_at]}</td>"
            f"</tr>"
        )

    table = "\n".join(trs) if trs else "<tr><td colspan=\"5\">No jobs yet</td></tr>"

    return f"""
<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Jobs</title>
    <style>
      body {{ font-family: ui-sans-serif, system-ui; margin: 24px; }}
      table {{ border-collapse: collapse; width: 100%; max-width: 1100px; }}
      th, td {{ border: 1px solid #e5e7eb; padding: 8px 10px; font-size: 14px; }}
      th {{ background: #f9fafb; text-align: left; }}
      a {{ color: #2563eb; }}
      .top {{ display:flex; gap: 12px; align-items:center; }}
    </style>
  </head>
  <body>
    <div class=\"top\">
      <h2 style=\"margin:0\">Jobs</h2>
      <a href=\"/ui/\">Create new</a>
    </div>
    <p>Showing latest {len(rows)} job(s).</p>
    <table>
      <thead>
        <tr>
          <th>Job ID</th>
          <th>Project</th>
          <th>Status</th>
          <th>Stage</th>
          <th>Updated</th>
        </tr>
      </thead>
      <tbody>
        {table}
      </tbody>
    </table>
  </body>
</html>
"""
