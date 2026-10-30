def add(a: int, b: int) -> int:
    return a - b  # deliberate bug


def test_add() -> None:
    assert add(2, 3) == 5
