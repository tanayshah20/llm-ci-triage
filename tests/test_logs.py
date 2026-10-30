from ci_triage.logs import MAX_LINE_CHARS, clean_log, error_excerpt


def test_clean_strips_bom_timestamps_and_ansi(failing_test_log: str) -> None:
    lines = clean_log(failing_test_log)
    assert lines[0] == "##[group]Run actions/checkout@v4"
    assert "E       assert -1 == 5" in lines
    assert not any("\x1b" in line or line.startswith("2026-") for line in lines)


def test_excerpt_ends_at_last_error_and_skips_cleanup(failing_test_log: str) -> None:
    excerpt = error_excerpt(clean_log(failing_test_log))
    assert excerpt[-1] == "Error: Process completed with exit code 1."
    assert "FAILED tests/test_math.py::test_add - assert -1 == 5" in excerpt
    assert not any("Cleaning up" in line for line in excerpt)


def test_excerpt_drops_group_markers_and_blank_lines(failing_test_log: str) -> None:
    excerpt = error_excerpt(clean_log(failing_test_log), max_lines=100)
    assert not any(line.startswith("##[") or not line.strip() for line in excerpt)


def test_excerpt_respects_max_lines(failing_test_log: str) -> None:
    assert len(error_excerpt(clean_log(failing_test_log), max_lines=3)) == 3


def test_excerpt_without_error_marker_uses_the_tail() -> None:
    assert error_excerpt(["a", "b", "c"], max_lines=2) == ["b", "c"]


def test_excerpt_of_empty_log() -> None:
    assert error_excerpt([]) == []


def test_long_lines_are_truncated() -> None:
    (line,) = error_excerpt(["x" * 1000])
    assert len(line) == MAX_LINE_CHARS and line.endswith("…")
