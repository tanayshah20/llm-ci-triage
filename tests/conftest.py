import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

FIXTURES = Path(__file__).parent / "fixtures"

Route = Callable[[httpx.Request], httpx.Response]


@pytest.fixture
def event_path() -> Path:
    return FIXTURES / "workflow_run_failure.json"


@pytest.fixture
def event_payload(event_path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(event_path.read_text(encoding="utf-8"))
    return data


@pytest.fixture
def jobs_payload() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / "jobs.json").read_text(encoding="utf-8"))
    return data


@pytest.fixture
def failing_test_log() -> str:
    return (FIXTURES / "logs" / "pytest_failure.txt").read_text(encoding="utf-8")


class FakeGitHub:
    """Routes `METHOD /path` to canned responses and records every request."""

    def __init__(self, routes: dict[str, Route | httpx.Response]) -> None:
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = self.routes.get(f"{request.method} {request.url.path}")
        if route is None:
            return httpx.Response(404, json={"message": "Not Found"})
        return route if isinstance(route, httpx.Response) else route(request)

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)

    def sent(self, method: str) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == method]
