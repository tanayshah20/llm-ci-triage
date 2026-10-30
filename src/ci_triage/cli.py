"""Entry point the Action runs: `python -m ci_triage`."""

from __future__ import annotations

import sys

import httpx

from ci_triage.config import ConfigError, Settings
from ci_triage.event import load_event
from ci_triage.github import GitHubClient
from ci_triage.summary import render_report
from ci_triage.triage import collect_failures, find_pull_request, upsert_comment


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
        report = render_report(event, collect_failures(gh, event.workflow_run))
        print(report)
        if settings.step_summary:
            with settings.step_summary.open("a", encoding="utf-8") as fh:
                fh.write(report)

        # A failed comment shouldn't turn the triage run red; the summary is already written.
        try:
            number = find_pull_request(gh, event)
            if number is None:
                print("ci-triage: no open pull request for this run; step summary only.")
                return 0
            result = upsert_comment(gh, number, event.workflow_run, report)
        except httpx.HTTPStatusError as exc:
            print(f"::warning::ci-triage could not comment: HTTP {exc.response.status_code}")
            return 0
    print(f"ci-triage: comment on #{number} {result}.")
    return 0
