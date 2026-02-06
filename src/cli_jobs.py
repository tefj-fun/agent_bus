#!/usr/bin/env python3
"""CLI for viewing job status and results."""

import asyncio
import sys
import time
from typing import Optional

import click
import httpx

DEFAULT_BASE_URL = "http://localhost:8000"


def get_client(base_url: str) -> httpx.Client:
    """Get HTTP client."""
    return httpx.Client(base_url=base_url, timeout=30.0)


@click.group()
@click.option("--url", default=DEFAULT_BASE_URL, help="API base URL")
@click.pass_context
def cli(ctx: click.Context, url: str) -> None:
    """Agent Bus job management CLI.

    View job status, watch progress, and retrieve results easily.
    """
    ctx.ensure_object(dict)
    ctx.obj["base_url"] = url


@cli.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all jobs."""
    base_url = ctx.obj["base_url"]

    with get_client(base_url) as client:
        try:
            resp = client.get("/api/projects/")
            resp.raise_for_status()
            jobs = resp.json()
        except httpx.RequestError as e:
            click.echo(f"Connection error: {e}", err=True)
            click.echo(f"Is the API running at {base_url}?", err=True)
            sys.exit(1)
        except httpx.HTTPStatusError as e:
            click.echo(f"API error: {e.response.status_code}", err=True)
            sys.exit(1)

    if not jobs:
        click.echo("No jobs found.")
        return

    click.echo(f"\n{'JOB ID':<40} {'STATUS':<15} {'STAGE':<20}")
    click.echo("-" * 75)

    for job in jobs:
        job_id = job.get("id", "")[:38]
        status = job.get("status", "unknown")
        stage = job.get("workflow_stage", "")

        # Status indicator
        if status == "completed":
            indicator = "done"
        elif status == "failed":
            indicator = "FAILED"
        elif status == "running":
            indicator = "running..."
        else:
            indicator = status

        click.echo(f"{job_id:<40} {indicator:<15} {stage:<20}")


@cli.command()
@click.argument("job_id")
@click.pass_context
def status(ctx: click.Context, job_id: str) -> None:
    """Show detailed status for a job."""
    base_url = ctx.obj["base_url"]

    with get_client(base_url) as client:
        try:
            resp = client.get(f"/api/projects/{job_id}")
            resp.raise_for_status()
            job = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                click.echo(f"Job '{job_id}' not found.", err=True)
            else:
                click.echo(f"API error: {e.response.status_code}", err=True)
            sys.exit(1)
        except httpx.RequestError as e:
            click.echo(f"Connection error: {e}", err=True)
            sys.exit(1)

    click.echo(f"\nJob: {job.get('id')}")
    click.echo(f"Project: {job.get('project_id')}")
    click.echo(f"Status: {job.get('status')}")
    click.echo(f"Stage: {job.get('workflow_stage')}")
    click.echo(f"Created: {job.get('created_at')}")
    click.echo(f"Updated: {job.get('updated_at')}")

    if job.get("completed_at"):
        click.echo(f"Completed: {job.get('completed_at')}")

    if job.get("latest_task"):
        task = job["latest_task"]
        click.echo(f"\nLatest Task: {task.get('agent_id')} - {task.get('status')}")


@cli.command()
@click.argument("job_id")
@click.option("--interval", default=3, help="Poll interval in seconds")
@click.pass_context
def watch(ctx: click.Context, job_id: str, interval: int) -> None:
    """Watch a job until completion.

    Polls the API and shows real-time progress updates.
    """
    base_url = ctx.obj["base_url"]
    last_stage = None

    click.echo(f"Watching job: {job_id}")
    click.echo(f"(Press Ctrl+C to stop)\n")

    with get_client(base_url) as client:
        while True:
            try:
                resp = client.get(f"/api/projects/{job_id}")
                resp.raise_for_status()
                job = resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    click.echo(f"Job '{job_id}' not found.", err=True)
                else:
                    click.echo(f"API error: {e.response.status_code}", err=True)
                sys.exit(1)
            except httpx.RequestError as e:
                click.echo(f"Connection error, retrying...", err=True)
                time.sleep(interval)
                continue

            status = job.get("status")
            stage = job.get("workflow_stage")

            # Print stage changes
            if stage != last_stage:
                timestamp = time.strftime("%H:%M:%S")
                click.echo(f"[{timestamp}] Stage: {stage}")
                last_stage = stage

            # Check if done
            if status == "completed":
                click.echo(f"\nJob completed!")
                click.echo(f"View results: agent-bus-jobs result {job_id}")
                break
            elif status == "failed":
                click.echo(f"\nJob failed!")
                if job.get("latest_task", {}).get("error"):
                    click.echo(f"Error: {job['latest_task']['error']}")
                break
            elif status == "waiting_approval":
                click.echo(f"\nWaiting for approval.")
                click.echo(f"Review PRD: {base_url}/ui/prd/{job_id}")
                break

            time.sleep(interval)


@cli.command()
@click.argument("job_id")
@click.option("--artifact", "-a", default=None, help="Specific artifact type")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def result(ctx: click.Context, job_id: str, artifact: Optional[str], as_json: bool) -> None:
    """Show results/artifacts for a completed job.

    Artifact types: prd, feature_tree, plan, architecture, ui_ux, development,
    qa, security, documentation, support_docs
    """
    base_url = ctx.obj["base_url"]

    artifact_types = [
        "prd",
        "feature_tree",
        "plan",
        "architecture",
        "ui_ux",
        "development",
        "qa",
        "security",
        "documentation",
        "support_docs",
    ]

    if artifact:
        if artifact not in artifact_types:
            click.echo(f"Unknown artifact type: {artifact}", err=True)
            click.echo(f"Valid types: {', '.join(artifact_types)}", err=True)
            sys.exit(1)
        types_to_fetch = [artifact]
    else:
        types_to_fetch = artifact_types

    with get_client(base_url) as client:
        # First check job status
        try:
            resp = client.get(f"/api/projects/{job_id}")
            resp.raise_for_status()
            job = resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                click.echo(f"Job '{job_id}' not found.", err=True)
            else:
                click.echo(f"API error: {e.response.status_code}", err=True)
            sys.exit(1)
        except httpx.RequestError as e:
            click.echo(f"Connection error: {e}", err=True)
            sys.exit(1)

        click.echo(f"\nJob: {job_id}")
        click.echo(f"Status: {job.get('status')}")
        click.echo(f"Stage: {job.get('workflow_stage')}\n")

        # Fetch artifacts
        found_any = False
        for art_type in types_to_fetch:
            try:
                resp = client.get(f"/api/projects/{job_id}/{art_type}")
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                data = resp.json()
            except (httpx.HTTPStatusError, httpx.RequestError):
                continue

            found_any = True
            content = data.get("content", "")

            if as_json:
                import json

                click.echo(json.dumps(data, indent=2))
            else:
                click.echo(f"=== {art_type.upper()} ===")
                click.echo()
                # Truncate very long content for display
                if len(content) > 5000:
                    click.echo(content[:5000])
                    click.echo(f"\n... (truncated, {len(content)} chars total)")
                else:
                    click.echo(content)
                click.echo()

        if not found_any:
            click.echo("No artifacts found yet.")
            click.echo(f"Job is at stage: {job.get('workflow_stage')}")


@cli.command()
@click.argument("job_id")
@click.option("--notes", default="", help="Approval notes")
@click.pass_context
def approve(ctx: click.Context, job_id: str, notes: str) -> None:
    """Approve a job's PRD to continue workflow."""
    base_url = ctx.obj["base_url"]

    with get_client(base_url) as client:
        try:
            resp = client.post(
                f"/api/projects/{job_id}/approve",
                json={"approved": True, "notes": notes},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            click.echo(f"Error: {e.response.text}", err=True)
            sys.exit(1)
        except httpx.RequestError as e:
            click.echo(f"Connection error: {e}", err=True)
            sys.exit(1)

    click.echo(f"Approved job: {job_id}")
    click.echo("Workflow will continue.")


def main() -> None:
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
