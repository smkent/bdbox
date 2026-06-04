"""Tests for console logging and output capture."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import call, patch

import pytest

from bdbox.timer import Timer

START_MS = 1138


def start_end(duration_ms: float, expected_str: str) -> Any:
    return pytest.param(
        START_MS,
        START_MS + duration_ms / 1000,
        expected_str,
        id=f"{duration_ms}",  # -{expected_str}",
    )


@pytest.mark.parametrize(
    ("start", "end", "expected_str"),
    [
        start_end(1, "1ms"),
        start_end(10, "10ms"),
        start_end(20, "20ms"),
        start_end(100, "100ms"),
        start_end(999, "999ms"),
        start_end(1000, "1.0s"),
        start_end(1001, "1.0s"),
        start_end(7749, "7.7s"),
        start_end(9949, "9.9s"),
        start_end(9951, "10.0s"),
        start_end(9999, "10.0s"),
        start_end(10000, "10s"),
        start_end(10001, "10s"),
        start_end((2187 - START_MS) * 1000, "17m 29s"),
        start_end(1000000, "16m 40s"),
        start_end(3600000, "1h 0m 0s"),
        start_end(10000000, "2h 46m 40s"),
        start_end(86400000, "1d 0h 0m 0s"),
        start_end(100000000, "1d 3h 46m 40s"),
        start_end(303030303, "3d 12h 10m 30s"),
        start_end(3030303030, "35d 1h 45m 3s"),
        start_end(30303030303, "350d 17h 30m 30s"),
        start_end(303030303030, "3507d 7h 5m 3s"),
    ],
    ids=lambda val: val if isinstance(val, str) else None,
)
def test_timer(start: float, end: float, expected_str: str) -> None:
    with patch.object(
        time, "monotonic", side_effect=[start, end]
    ) as mock_time:
        timer = Timer()
        assert timer.stopped is None
        timer.stop()
        assert timer.stopped is not None
        assert timer.elapsed_ms == round((end - start) * 1000)
        assert str(timer) == expected_str
        assert timer.elapsed_str == expected_str
    assert mock_time.call_args_list == [call()] * 2
