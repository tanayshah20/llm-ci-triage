import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from ci_triage import cli
from ci_triage.event import WorkflowRunEvent, load_event
from ci_triage.github import GitHubClient, Job
from ci_triage.summary import render_summary


def set_env(monkeypatch: pytest.MonkeyPatch, event_path: Path, summary: Path) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "t0ken")
    monkeypatch.setenv("GITHUB_REPOSITORY", "octo/sandbox")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_run")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))


def test_main_writes_step_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    event_path: Path,
    jobs_payload: dict[str, Any],
) -> None:
    summary = tmp_path / "summary.md"
    set_env(monkeypatch, event_path, summary)
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=jobs_payload))

    def client(token: str, repo: str, *, base_url: str) -> GitHubClient:
        return GitHubClient(token, repo, base_url=base_url, transport=transport)

    monkeypatch.setattr(cli, "GitHubClient", client)

    assert cli.main() == 0
    text = summary.read_text(encoding="utf-8")
    assert "[test](" in text and "`Run pytest`" in text
    assert "#7" in text


def test_main_skips_successful_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, event_payload: dict[str, Any]
) -> None:
    event_payload["workflow_run"]["conclusion"] = "success"
    path = tmp_path / "event.json"
    path.write_text(json.dumps(event_payload), encoding="utf-8")
    summary = tmp_path / "summary.md"
    set_env(monkeypatch, path, summary)

    assert cli.main() == 0
    assert not summary.exists()


def test_main_reports_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert cli.main() == 2


def test_summary_without_jobs(event_path: Path) -> None:
    text = render_summary(load_event(event_path), [])
    assert "No failed jobs found" in text


def test_summary_mentions_fork(event_payload: dict[str, Any]) -> None:
    event_payload["workflow_run"]["pull_requests"] = []
    event_payload["workflow_run"]["head_repository"]["full_name"] = "someone/sandbox"
    event = WorkflowRunEvent.model_validate(event_payload)
    job = Job(id=1, name="test", html_url="https://example.invalid")
    assert "from a fork" in render_summary(event, [job])
