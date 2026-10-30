from pathlib import Path
from typing import Any

from ci_triage.event import WorkflowRunEvent, load_event


def test_load_failure_event(event_path: Path) -> None:
    event = load_event(event_path)
    assert event.is_failure
    assert not event.is_from_fork
    assert [pr.number for pr in event.workflow_run.pull_requests] == [7]


def test_success_is_not_a_failure(event_payload: dict[str, Any]) -> None:
    event_payload["workflow_run"]["conclusion"] = "success"
    assert not WorkflowRunEvent.model_validate(event_payload).is_failure


def test_requested_action_is_not_a_failure(event_payload: dict[str, Any]) -> None:
    event_payload["action"] = "requested"
    assert not WorkflowRunEvent.model_validate(event_payload).is_failure


def test_fork_pr_has_no_pull_requests(event_payload: dict[str, Any]) -> None:
    event_payload["workflow_run"]["pull_requests"] = []
    event_payload["workflow_run"]["head_repository"]["full_name"] = "someone/sandbox"
    event = WorkflowRunEvent.model_validate(event_payload)
    assert event.is_from_fork
    assert event.workflow_run.pull_requests == []
