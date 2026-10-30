"""Markdown shown in the workflow's step summary (and, from week 2, the PR comment)."""

from __future__ import annotations

from ci_triage.event import WorkflowRunEvent
from ci_triage.github import Job


def render_summary(event: WorkflowRunEvent, jobs: list[Job]) -> str:
    run = event.workflow_run
    lines = [
        f"## CI triage: [{run.name}]({run.html_url}) failed",
        "",
        f"- Commit: `{run.head_sha[:7]}` on `{run.head_branch or 'unknown'}`",
        f"- Attempt: {run.run_attempt}",
    ]
    if run.pull_requests:
        prs = ", ".join(f"#{pr.number}" for pr in run.pull_requests)
        lines.append(f"- Pull request: {prs}")
    elif event.is_from_fork:
        lines.append("- Pull request: from a fork (lookup by commit not implemented yet)")

    lines += ["", "### Failed jobs", ""]
    if not jobs:
        lines.append("No failed jobs found; the run may have failed before any job started.")
    for job in jobs:
        step = job.failed_step
        where = f" at step {step.number} `{step.name}`" if step else ""
        lines.append(f"- [{job.name}]({job.html_url}){where}")
    return "\n".join(lines) + "\n"
