"""The triage pipeline: collect failures, find the PR, post or update the comment."""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

from ci_triage.event import WorkflowRun, WorkflowRunEvent
from ci_triage.github import GitHubClient, Job
from ci_triage.logs import clean_log, error_excerpt

# One comment per (PR, workflow). The run id lets an older run that finishes late
# avoid overwriting a newer run's comment.
MARKER_RE = re.compile(r"<!-- ci-triage workflow=(\d+) run=(\d+) -->")


@dataclass(frozen=True)
class JobFailure:
    job: Job
    excerpt: list[str]
    error: str | None = None  # set when the log couldn't be downloaded


def collect_failures(gh: GitHubClient, run: WorkflowRun) -> list[JobFailure]:
    failures: list[JobFailure] = []
    for job in gh.failed_jobs(run.id, run.run_attempt):
        try:
            raw = gh.job_log(job.id)
        except httpx.HTTPError as exc:
            failures.append(JobFailure(job, [], f"Could not download the log ({exc})."))
            continue
        failures.append(JobFailure(job, error_excerpt(clean_log(raw))))
    return failures


def find_pull_request(gh: GitHubClient, event: WorkflowRunEvent) -> int | None:
    run = event.workflow_run
    if run.pull_requests:
        return run.pull_requests[0].number
    # Empty for PRs from forks: look the PR up by its head branch and commit instead.
    head = run.head_repository
    if head is None or not run.head_branch:
        return None
    for pr in gh.open_pulls_for_head(head.owner, run.head_branch):
        if pr.head.sha == run.head_sha:
            return pr.number
    return None


def marker(run: WorkflowRun) -> str:
    return f"<!-- ci-triage workflow={run.workflow_id} run={run.id} -->"


def upsert_comment(gh: GitHubClient, number: int, run: WorkflowRun, report: str) -> str:
    """Create or update this workflow's comment on the PR; returns what happened."""
    body = f"{marker(run)}\n{report}"
    for comment in gh.issue_comments(number):
        match = MARKER_RE.match(comment.body)
        if not match or comment.user is None or comment.user.type != "Bot":
            continue
        if int(match[1]) != run.workflow_id:
            continue
        if int(match[2]) > run.id:
            return "skipped (a newer run already commented)"
        gh.update_comment(comment.id, body)
        return "updated"
    gh.create_comment(number, body)
    return "created"
