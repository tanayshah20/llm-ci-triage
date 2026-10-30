import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from ci_triage import cli
from ci_triage.github import GitHubClient
from tests.conftest import FakeGitHub

JOBS = "GET /repos/octo/sandbox/actions/runs/9876543210/attempts/1/jobs"
LOG = "GET /repos/octo/sandbox/actions/jobs/111/logs"
COMMENTS = "/repos/octo/sandbox/issues/7/comments"


def set_env(monkeypatch: pytest.MonkeyPatch, event_path: Path, summary: Path) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "t0ken")
    monkeypatch.setenv("GITHUB_REPOSITORY", "octo/sandbox")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_run")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))


def use_fake(monkeypatch: pytest.MonkeyPatch, fake: FakeGitHub) -> None:
    def client(token: str, repo: str, *, base_url: str) -> GitHubClient:
        return GitHubClient(token, repo, base_url=base_url, transport=fake.transport)

    monkeypatch.setattr(cli, "GitHubClient", client)


def test_main_writes_summary_and_comments(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    event_path: Path,
    jobs_payload: dict[str, Any],
    failing_test_log: str,
) -> None:
    summary = tmp_path / "summary.md"
    set_env(monkeypatch, event_path, summary)
    fake = FakeGitHub(
        {
            JOBS: httpx.Response(200, json=jobs_payload),
            LOG: httpx.Response(200, text=failing_test_log),
            f"GET {COMMENTS}": httpx.Response(200, json=[]),
            f"POST {COMMENTS}": httpx.Response(201, json={}),
        }
    )
    use_fake(monkeypatch, fake)

    assert cli.main() == 0
    text = summary.read_text(encoding="utf-8")
    assert "[test](" in text and "`Run pytest`" in text
    assert "FAILED tests/test_math.py::test_add" in text

    (post,) = fake.sent("POST")
    body = json.loads(post.content)["body"]
    assert body.startswith("<!-- ci-triage workflow=555 run=9876543210 -->")
    assert "FAILED tests/test_math.py::test_add" in body


def test_main_survives_comment_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    event_path: Path,
    jobs_payload: dict[str, Any],
    failing_test_log: str,
) -> None:
    summary = tmp_path / "summary.md"
    set_env(monkeypatch, event_path, summary)
    fake = FakeGitHub(
        {
            JOBS: httpx.Response(200, json=jobs_payload),
            LOG: httpx.Response(200, text=failing_test_log),
            f"GET {COMMENTS}": httpx.Response(403, json={"message": "Forbidden"}),
        }
    )
    use_fake(monkeypatch, fake)

    assert cli.main() == 0
    assert summary.exists()


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
