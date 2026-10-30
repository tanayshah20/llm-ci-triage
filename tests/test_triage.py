import json
from typing import Any

import httpx

from ci_triage.event import WorkflowRunEvent
from ci_triage.github import GitHubClient, Job
from ci_triage.summary import render_report
from ci_triage.triage import (
    JobFailure,
    collect_failures,
    find_pull_request,
    marker,
    upsert_comment,
)
from tests.conftest import FakeGitHub

JOBS = "GET /repos/octo/sandbox/actions/runs/9876543210/attempts/1/jobs"
LOG = "GET /repos/octo/sandbox/actions/jobs/111/logs"
PULLS = "GET /repos/octo/sandbox/pulls"
COMMENTS = "GET /repos/octo/sandbox/issues/7/comments"
BOT = {"login": "github-actions[bot]", "type": "Bot"}


def client(fake: FakeGitHub) -> GitHubClient:
    return GitHubClient("t0ken", "octo/sandbox", transport=fake.transport)


def fork_event(payload: dict[str, Any]) -> WorkflowRunEvent:
    payload["workflow_run"]["pull_requests"] = []
    payload["workflow_run"]["head_repository"]["full_name"] = "someone/sandbox"
    return WorkflowRunEvent.model_validate(payload)


def test_collect_failures_reads_each_log(
    event_payload: dict[str, Any], jobs_payload: dict[str, Any], failing_test_log: str
) -> None:
    fake = FakeGitHub(
        {
            JOBS: httpx.Response(200, json=jobs_payload),
            LOG: httpx.Response(200, text=failing_test_log),
        }
    )
    event = WorkflowRunEvent.model_validate(event_payload)
    with client(fake) as gh:
        (failure,) = collect_failures(gh, event.workflow_run)

    assert failure.error is None
    assert failure.excerpt[-1] == "Error: Process completed with exit code 1."


def test_collect_failures_survives_missing_log(
    event_payload: dict[str, Any], jobs_payload: dict[str, Any]
) -> None:
    fake = FakeGitHub({JOBS: httpx.Response(200, json=jobs_payload)})  # log route 404s
    event = WorkflowRunEvent.model_validate(event_payload)
    with client(fake) as gh:
        (failure,) = collect_failures(gh, event.workflow_run)

    assert failure.excerpt == []
    assert failure.error is not None and "Could not download" in failure.error


def test_pull_request_from_event(event_payload: dict[str, Any]) -> None:
    fake = FakeGitHub({})
    with client(fake) as gh:
        assert find_pull_request(gh, WorkflowRunEvent.model_validate(event_payload)) == 7
    assert fake.requests == []


def test_fork_pull_request_found_by_head(event_payload: dict[str, Any]) -> None:
    sha = event_payload["workflow_run"]["head_sha"]
    pulls = [{"number": 3, "head": {"sha": "old"}}, {"number": 8, "head": {"sha": sha}}]
    fake = FakeGitHub({PULLS: httpx.Response(200, json=pulls)})
    with client(fake) as gh:
        assert find_pull_request(gh, fork_event(event_payload)) == 8
    assert fake.requests[0].url.params["head"] == "someone:broken-test"


def test_no_pull_request_when_head_moved_on(event_payload: dict[str, Any]) -> None:
    fake = FakeGitHub({PULLS: httpx.Response(200, json=[{"number": 8, "head": {"sha": "new"}}])})
    with client(fake) as gh:
        assert find_pull_request(gh, fork_event(event_payload)) is None


def test_upsert_creates_first_comment(event_payload: dict[str, Any]) -> None:
    fake = FakeGitHub(
        {
            COMMENTS: httpx.Response(200, json=[{"id": 1, "body": "nice PR", "user": BOT}]),
            "POST /repos/octo/sandbox/issues/7/comments": httpx.Response(201, json={}),
        }
    )
    run = WorkflowRunEvent.model_validate(event_payload).workflow_run
    with client(fake) as gh:
        assert upsert_comment(gh, 7, run, "report") == "created"

    body = json.loads(fake.sent("POST")[0].content)["body"]
    assert body == f"{marker(run)}\nreport"


def test_upsert_updates_own_comment(event_payload: dict[str, Any]) -> None:
    run = WorkflowRunEvent.model_validate(event_payload).workflow_run
    old = f"<!-- ci-triage workflow={run.workflow_id} run={run.id - 1} -->\nold"
    fake = FakeGitHub(
        {
            COMMENTS: httpx.Response(200, json=[{"id": 42, "body": old, "user": BOT}]),
            "PATCH /repos/octo/sandbox/issues/comments/42": httpx.Response(200, json={}),
        }
    )
    with client(fake) as gh:
        assert upsert_comment(gh, 7, run, "report") == "updated"
    assert fake.sent("POST") == []


def test_upsert_ignores_other_workflows_and_humans(event_payload: dict[str, Any]) -> None:
    run = WorkflowRunEvent.model_validate(event_payload).workflow_run
    other_workflow = f"<!-- ci-triage workflow=1 run={run.id} -->"
    spoofed = marker(run)
    comments = [
        {"id": 1, "body": other_workflow, "user": BOT},
        {"id": 2, "body": spoofed, "user": {"login": "mallory", "type": "User"}},
    ]
    fake = FakeGitHub(
        {
            COMMENTS: httpx.Response(200, json=comments),
            "POST /repos/octo/sandbox/issues/7/comments": httpx.Response(201, json={}),
        }
    )
    with client(fake) as gh:
        assert upsert_comment(gh, 7, run, "report") == "created"
    assert fake.sent("PATCH") == []


def test_upsert_keeps_newer_runs_comment(event_payload: dict[str, Any]) -> None:
    run = WorkflowRunEvent.model_validate(event_payload).workflow_run
    newer = f"<!-- ci-triage workflow={run.workflow_id} run={run.id + 1} -->"
    fake = FakeGitHub({COMMENTS: httpx.Response(200, json=[{"id": 5, "body": newer, "user": BOT}])})
    with client(fake) as gh:
        assert upsert_comment(gh, 7, run, "report").startswith("skipped")
    assert fake.sent("PATCH") == [] and fake.sent("POST") == []


def test_report_fences_untrusted_backticks(event_payload: dict[str, Any]) -> None:
    event = WorkflowRunEvent.model_validate(event_payload)
    job = Job(id=1, name="te`st", html_url="https://example.invalid")
    report = render_report(event, [JobFailure(job, ["```", "@someone ping"])])
    assert "````text" in report
    assert "[te'st]" in report


def test_report_without_failures(event_payload: dict[str, Any]) -> None:
    report = render_report(WorkflowRunEvent.model_validate(event_payload), [])
    assert "No failed jobs found" in report
