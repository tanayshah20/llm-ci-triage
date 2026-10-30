import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


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
