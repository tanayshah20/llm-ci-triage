"""Clean raw job logs and pull out the lines around the failure."""

from __future__ import annotations

import re

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
# Every line of a downloaded job log starts with an ISO-8601 timestamp.
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z ?")

BOM = "\ufeff"

EXCERPT_LINES = 30
MAX_LINE_CHARS = 300

# Workflow-command prefixes GitHub writes into logs, and what to show instead.
_COMMANDS = {
    "##[error]": "Error: ",
    "##[warning]": "Warning: ",
    "##[notice]": "Notice: ",
    "##[command]": "$ ",
}
_HIDDEN = ("##[group]", "##[endgroup]", "##[debug]")


def clean_log(raw: str) -> list[str]:
    """Strip the BOM, timestamps and ANSI colour codes from a raw job log."""
    return [
        ANSI_RE.sub("", TIMESTAMP_RE.sub("", line)).rstrip()
        for line in raw.lstrip(BOM).splitlines()
    ]


def error_excerpt(lines: list[str], max_lines: int = EXCERPT_LINES) -> list[str]:
    """The last `max_lines` lines up to GitHub's final `##[error]` marker.

    Post-job cleanup steps run after the failure, so the last error marker is a
    better anchor than the end of the log. Week 3 replaces this with a real reducer.
    """
    end = len(lines) - 1
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("##[error]"):
            end = i
            break

    picked: list[str] = []
    for line in reversed(lines[: end + 1]):
        if not line.strip() or line.startswith(_HIDDEN):
            continue
        picked.append(_display(line))
        if len(picked) == max_lines:
            break
    picked.reverse()
    return picked


def _display(line: str) -> str:
    for prefix, label in _COMMANDS.items():
        if line.startswith(prefix):
            line = label + line[len(prefix) :]
            break
    if len(line) > MAX_LINE_CHARS:
        line = line[: MAX_LINE_CHARS - 1] + "…"
    return line
