"""Markdown report used for both the step summary and the PR comment."""

from __future__ import annotations

from ci_triage.event import WorkflowRunEvent
from ci_triage.triage import JobFailure

# Keeps the comment well under GitHub's 65,536-character limit.
MAX_JOBS = 5


def render_report(event: WorkflowRunEvent, failures: list[JobFailure]) -> str:
    run = event.workflow_run
    lines = [
        f"## ❌ CI triage: [{_plain(run.name)}]({run.html_url}) failed",
        "",
        f"Commit `{run.head_sha[:7]}` on `{_plain(run.head_branch or 'unknown')}`"
        f" · attempt {run.run_attempt}",
        "",
    ]
    if not failures:
        lines += ["No failed jobs found; the run may have failed before any job started.", ""]

    for failure in failures[:MAX_JOBS]:
        job = failure.job
        step = job.failed_step
        where = f" at step `{_plain(step.name)}`" if step else ""
        lines += [f"### [{_plain(job.name)}]({job.html_url}) failed{where}", ""]
        if failure.error:
            lines += [f"_{failure.error}_", ""]
        elif failure.excerpt:
            lines += [*_code_block(failure.excerpt), ""]
        else:
            lines += ["_The log is empty._", ""]

    if len(failures) > MAX_JOBS:
        lines += [f"…and {len(failures) - MAX_JOBS} more failed jobs.", ""]
    lines.append("<sub>Posted by ci-triage. Root-cause analysis comes in a later version.</sub>")
    return "\n".join(lines) + "\n"


def _plain(text: str) -> str:
    """Names come from workflow files and branches; keep them from breaking the markdown."""
    return text.replace("`", "'").replace("[", "(").replace("]", ")")


def _code_block(lines: list[str]) -> list[str]:
    # Log text is untrusted: a fence longer than any backtick run inside it can't be
    # closed early, and @mentions inside a code block don't notify anyone.
    longest = max((_longest_backtick_run(line) for line in lines), default=0)
    fence = "`" * max(3, longest + 1)
    return [f"{fence}text", *lines, fence]


def _longest_backtick_run(line: str) -> int:
    best = current = 0
    for char in line:
        current = current + 1 if char == "`" else 0
        best = max(best, current)
    return best
