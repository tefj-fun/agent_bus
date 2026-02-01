"""UI POST handlers for HITL actions.

Separated to keep ui_prd.py focused on rendering.
"""

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from .projects import ApprovalRequest, approve_job, request_changes

router = APIRouter()


@router.post("/prd/{job_id}/approve", response_class=HTMLResponse)
async def ui_approve(job_id: str, notes: str = Form(default="")):
    await approve_job(job_id, ApprovalRequest(notes=notes or None))
    return (
        f"<p>Approved <code>{job_id}</code>.</p>"
        f"<p><a href='/ui/jobs'>Back to jobs</a> | <a href='/ui/prd/{job_id}'>Back to PRD</a></p>"
    )


@router.post("/prd/{job_id}/request_changes", response_class=HTMLResponse)
async def ui_request_changes(job_id: str, notes: str = Form(default="")):
    await request_changes(job_id, ApprovalRequest(notes=notes or None))
    return (
        f"<p>Requested changes for <code>{job_id}</code>.</p>"
        f"<p><a href='/ui/jobs'>Back to jobs</a> | <a href='/ui/prd/{job_id}'>Back to PRD</a></p>"
    )
