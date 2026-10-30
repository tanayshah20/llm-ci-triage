"""The subset of the `workflow_run` webhook payload that triage needs."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class Repository(BaseModel):
    full_name: str


class PullRequestRef(BaseModel):
    number: int


class WorkflowRun(BaseModel):
    id: int
    name: str
    html_url: str
    event: str
    head_sha: str
    head_branch: str | None = None
    run_attempt: int = 1
    conclusion: str | None = None
    # Empty for PRs opened from forks; later weeks fall back to a head_sha lookup.
    pull_requests: list[PullRequestRef] = []
    head_repository: Repository | None = None


class WorkflowRunEvent(BaseModel):
    action: str
    workflow_run: WorkflowRun
    repository: Repository

    @property
    def is_failure(self) -> bool:
        return self.action == "completed" and self.workflow_run.conclusion == "failure"

    @property
    def is_from_fork(self) -> bool:
        head = self.workflow_run.head_repository
        return head is not None and head.full_name != self.repository.full_name


def load_event(path: Path) -> WorkflowRunEvent:
    return WorkflowRunEvent.model_validate_json(path.read_text(encoding="utf-8"))
