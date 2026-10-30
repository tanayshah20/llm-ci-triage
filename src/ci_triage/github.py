"""Minimal GitHub REST client: only the endpoints triage uses."""

from __future__ import annotations

from types import TracebackType

import httpx
from pydantic import BaseModel

API_VERSION = "2022-11-28"
PAGE_SIZE = 100


class Step(BaseModel):
    name: str
    number: int
    conclusion: str | None = None


class Job(BaseModel):
    id: int
    name: str
    html_url: str
    conclusion: str | None = None
    steps: list[Step] = []

    @property
    def failed_step(self) -> Step | None:
        return next((s for s in self.steps if s.conclusion == "failure"), None)


class GitHubClient:
    def __init__(
        self,
        token: str,
        repository: str,
        *,
        base_url: str = "https://api.github.com",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.repository = repository
        self._http = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
            },
            timeout=30.0,
            follow_redirects=True,
            transport=transport,
        )

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._http.close()

    def jobs_for_attempt(self, run_id: int, attempt: int) -> list[Job]:
        path = f"/repos/{self.repository}/actions/runs/{run_id}/attempts/{attempt}/jobs"
        jobs: list[Job] = []
        page = 1
        while True:
            resp = self._http.get(path, params={"per_page": PAGE_SIZE, "page": page})
            resp.raise_for_status()
            body = resp.json()
            jobs.extend(Job.model_validate(j) for j in body["jobs"])
            if len(jobs) >= body["total_count"] or not body["jobs"]:
                return jobs
            page += 1

    def failed_jobs(self, run_id: int, attempt: int) -> list[Job]:
        return [j for j in self.jobs_for_attempt(run_id, attempt) if j.conclusion == "failure"]
