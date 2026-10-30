"""Entry point the Action runs: `python -m ci_triage`."""

from __future__ import annotations

import sys

from ci_triage.config import ConfigError, Settings
from ci_triage.event import load_event
from ci_triage.github import GitHubClient
from ci_triage.summary import render_summary


def main() -> int:
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"ci-triage: {exc}", file=sys.stderr)
        return 2

    if settings.event_name != "workflow_run":
        print(f"ci-triage: expected a workflow_run event, got {settings.event_name}; skipping.")
        return 0

    event = load_event(settings.event_path)
    if not event.is_failure:
        print(f"ci-triage: run concluded {event.workflow_run.conclusion!r}; nothing to triage.")
        return 0

    with GitHubClient(settings.token, settings.repository, base_url=settings.api_url) as gh:
        jobs = gh.failed_jobs(event.workflow_run.id, event.workflow_run.run_attempt)

    summary = render_summary(event, jobs)
    print(summary)
    if settings.step_summary:
        with settings.step_summary.open("a", encoding="utf-8") as fh:
            fh.write(summary)
    return 0
