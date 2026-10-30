from typing import Any

import httpx

from ci_triage.github import GitHubClient
from tests.conftest import FakeGitHub

JOBS = "GET /repos/octo/sandbox/actions/runs/9876543210/attempts/1/jobs"


def make_client(fake: FakeGitHub) -> GitHubClient:
    return GitHubClient("t0ken", "octo/sandbox", transport=fake.transport)


def test_failed_jobs_filters_and_finds_step(jobs_payload: dict[str, Any]) -> None:
    fake = FakeGitHub({JOBS: httpx.Response(200, json=jobs_payload)})

    with make_client(fake) as gh:
        jobs = gh.failed_jobs(9876543210, 1)

    assert [j.name for j in jobs] == ["test"]
    step = jobs[0].failed_step
    assert step is not None and step.name == "Run pytest"
    assert fake.requests[0].headers["Authorization"] == "Bearer t0ken"


def test_jobs_paginate(jobs_payload: dict[str, Any]) -> None:
    job = jobs_payload["jobs"][0]

    def page(request: httpx.Request) -> httpx.Response:
        n = int(request.url.params["page"])
        return httpx.Response(200, json={"total_count": 2, "jobs": [{**job, "id": n}]})

    fake = FakeGitHub({"GET /repos/octo/sandbox/actions/runs/1/attempts/1/jobs": page})
    with make_client(fake) as gh:
        assert [j.id for j in gh.jobs_for_attempt(1, 1)] == [1, 2]


def test_job_log_follows_redirect_without_leaking_token() -> None:
    signed = "https://results-receiver.actions.githubusercontent.com/log?sig=abc"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.github.com":
            return httpx.Response(302, headers={"Location": signed})
        return httpx.Response(200, text="hello log")

    fake = FakeGitHub(
        {"GET /repos/octo/sandbox/actions/jobs/111/logs": handler, "GET /log": handler}
    )
    with make_client(fake) as gh:
        assert gh.job_log(111) == "hello log"

    redirected = fake.requests[1]
    assert redirected.url.host == "results-receiver.actions.githubusercontent.com"
    assert "Authorization" not in redirected.headers


def test_open_pulls_for_head_filters_by_owner_and_branch() -> None:
    fake = FakeGitHub(
        {
            "GET /repos/octo/sandbox/pulls": httpx.Response(
                200, json=[{"number": 9, "head": {"sha": "abc"}}]
            )
        }
    )
    with make_client(fake) as gh:
        pulls = gh.open_pulls_for_head("someone", "fix-it")

    assert [p.number for p in pulls] == [9]
    assert fake.requests[0].url.params["head"] == "someone:fix-it"
    assert fake.requests[0].url.params["state"] == "open"


def test_issue_comments_paginate() -> None:
    def page(request: httpx.Request) -> httpx.Response:
        n = int(request.url.params["page"])
        size = 100 if n == 1 else 1
        return httpx.Response(200, json=[{"id": n * 1000 + i, "body": ""} for i in range(size)])

    fake = FakeGitHub({"GET /repos/octo/sandbox/issues/7/comments": page})
    with make_client(fake) as gh:
        assert len(gh.issue_comments(7)) == 101
