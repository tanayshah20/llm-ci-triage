"""Settings read from the environment GitHub Actions provides."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


class ConfigError(RuntimeError):
    """A required environment variable is missing."""


@dataclass(frozen=True)
class Settings:
    token: str
    repository: str
    event_name: str
    event_path: Path
    step_summary: Path | None
    api_url: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env

        def required(name: str) -> str:
            value = env.get(name)
            if not value:
                raise ConfigError(f"{name} is not set; is this running inside GitHub Actions?")
            return value

        summary = env.get("GITHUB_STEP_SUMMARY")
        return cls(
            token=required("GITHUB_TOKEN"),
            repository=required("GITHUB_REPOSITORY"),
            event_name=required("GITHUB_EVENT_NAME"),
            event_path=Path(required("GITHUB_EVENT_PATH")),
            step_summary=Path(summary) if summary else None,
            api_url=env.get("GITHUB_API_URL", "https://api.github.com"),
        )
