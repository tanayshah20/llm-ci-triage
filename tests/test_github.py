from typing import Any

import httpx

from ci_triage.github import GitHubClient


def make_client(handler: Any) -> GitHubClient:
    return GitHubClient("t0ken", "octo/sandbox", transport=httpx.MockTransport(handler))


def test_failed_jobs_filters_and_finds_step(jobs_payload: dict[str, Any]) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=jobs_payload)

    with make_client(handler) as gh:
        jobs = gh.failed_jobs(9876543210, 1)

    assert [j.name for j in jobs] == ["test"]
    step = jobs[0].failed_step
    assert step is not None and step.name == "Run pytest"
    assert seen[0].url.path == "/repos/octo/sandbox/actions/runs/9876543210/attempts/1/jobs"
    assert seen[0].headers["Authorization"] == "Bearer t0ken"


def test_jobs_paginate(jobs_payload: dict[str, Any]) -> None:
    job = jobs_payload["jobs"][0]

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        return httpx.Response(200, json={"total_count": 2, "jobs": [{**job, "id": page}]})

    with make_client(handler) as gh:
        jobs = gh.jobs_for_attempt(1, 1)

    assert [j.id for j in jobs] == [1, 2]
