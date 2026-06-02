"""Tests for console logging and output capture."""

from __future__ import annotations

import io
import logging
import sys
from contextlib import suppress
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from bdbox.console import LoggingStream, LogLevel, console
from bdbox.protocol import ConsoleMessage
from bdbox.view.console import WebStream

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


@pytest.fixture(autouse=True)
def console_verbosity() -> None:
    """Disable console verbosity override in console tests."""
    return


@pytest.fixture(autouse=True)
def reset_console() -> None:
    console.reset()


@dataclass
class LogStreamTest:
    logname = "bdbox.stream_test"
    caplog: pytest.LogCaptureFixture

    @cached_property
    def logger(self) -> logging.Logger:
        return logging.getLogger(self.logname)

    @cached_property
    def stream(self) -> LoggingStream:
        return LoggingStream(self.logger, LogLevel.STDOUT)

    @property
    def records(self) -> Sequence[Any]:
        return [
            r for r in self.caplog.records if r.name == "bdbox.stream_test"
        ]

    def records_level(self, level: int) -> Sequence[Any]:
        return [r for r in self.caplog.records if r.levelno == level]


@pytest.fixture
def log_stream(caplog: pytest.LogCaptureFixture) -> Iterator[LogStreamTest]:
    instance = LogStreamTest(caplog=caplog)
    with caplog.at_level(LogLevel.TRACE, logger=instance.logname):
        yield instance


def _stream_records(
    caplog: pytest.LogCaptureFixture,
) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "bdbox.stream_test"]


@pytest.fixture
def stream(caplog: pytest.LogCaptureFixture) -> Iterator[LoggingStream]:
    logger = logging.getLogger("bdbox.stream_test")
    with caplog.at_level(LogLevel.TRACE, logger="bdbox.stream_test"):
        yield LoggingStream(logger, LogLevel.STDOUT)


def test_logging_stream_complete_line_emits_record(
    log_stream: LogStreamTest,
) -> None:
    log_stream.stream.write("there goes another one\n")
    assert len(log_stream.records) == 1
    assert log_stream.records[0].message == "there goes another one"
    assert log_stream.records[0].levelno == LogLevel.STDOUT


def test_logging_stream_partial_line_not_emitted(
    log_stream: LogStreamTest,
) -> None:
    log_stream.stream.write("no newline")
    assert not log_stream.records
    assert log_stream.stream.buf == "no newline"


def test_logging_stream_multiple_lines_one_write(
    log_stream: LogStreamTest,
) -> None:
    log_stream.stream.write("how\nare\nyou\n")
    assert [r.message for r in log_stream.records] == [
        "how",
        "are",
        "you",
    ]


def test_logging_stream_partial_lines_across_writes(
    log_stream: LogStreamTest,
) -> None:
    log_stream.stream.write("large leak, ve")
    log_stream.stream.write("ry dangerous\n")
    assert len(log_stream.records) == 1
    assert log_stream.records[0].message == "large leak, very dangerous"


def test_logging_stream_trailing_newline_no_empty_record(
    log_stream: LogStreamTest,
) -> None:
    log_stream.stream.write("message with newline\n")
    assert len(log_stream.records) == 1
    assert log_stream.stream.buf == ""


def test_logging_stream_flush_emits_buffered_content(
    log_stream: LogStreamTest,
) -> None:
    log_stream.stream.write("message without newline")
    assert not log_stream.records
    log_stream.stream.flush()
    assert len(log_stream.records) == 1
    assert log_stream.records[0].message == "message without newline"
    assert log_stream.stream.buf == ""


def test_logging_stream_flush_ignores_whitespace_only_buffer(
    log_stream: LogStreamTest,
) -> None:
    log_stream.stream.buf = "   \n  "
    log_stream.stream.flush()
    assert not log_stream.records


def test_logging_stream_flush_clears_buffer(log_stream: LogStreamTest) -> None:
    log_stream.stream.buf = "goop"
    log_stream.stream.flush()
    assert log_stream.stream.buf == ""


def test_logging_stream_write_returns_length(
    log_stream: LogStreamTest,
) -> None:
    assert log_stream.stream.write("hello\n") == 6
    assert log_stream.stream.write("no newline") == 10


def test_logging_stream_isatty_false(log_stream: LogStreamTest) -> None:
    assert log_stream.stream.isatty() is False


def test_web_stream_write() -> None:
    value = "I can't see a thing in this helmet"
    s = WebStream()
    assert s.write(value) == len(value)
    assert s.q.get_nowait() == ConsoleMessage(text=value)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("   \n   ", id="whitespace"),
        pytest.param("", id="empty"),
    ],
)
def test_web_stream_write_whitespace_only_not_queued(value: str) -> None:
    s = WebStream()
    s.write(value)
    assert s.q.empty()


def _bdbox_records(
    caplog: pytest.LogCaptureFixture, level: int
) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.levelno == level]


@pytest.mark.parametrize(
    ("level", "stream_attr"),
    [
        pytest.param(LogLevel.STDOUT, "stdout", id="STDOUT"),
        pytest.param(LogLevel.STDERR, "stderr", id="STDERR"),
    ],
)
def test_log_stdout_stderr(
    log_stream: LogStreamTest, level: int, stream_attr: str
) -> None:
    original_stdout, original_stderr = sys.stdout, sys.stderr
    with (
        log_stream.caplog.at_level(level, logger="bdbox"),
        console.log_stdout_stderr(),
    ):
        print("we're all fine, here, now", file=getattr(sys, stream_attr))
    records = log_stream.records_level(level)
    assert len(records) == 1
    assert records[0].message == "we're all fine, here, now"
    assert sys.stdout is original_stdout
    assert sys.stderr is original_stderr


@pytest.mark.parametrize(
    ("level", "stream_attr"),
    [
        pytest.param(LogLevel.STDOUT, "stdout", id="STDOUT"),
        pytest.param(LogLevel.STDERR, "stderr", id="STDERR"),
    ],
)
def test_log_stdout_stderr_flushes_partial_on_exit(
    log_stream: LogStreamTest, level: int, stream_attr: str
) -> None:
    with (
        log_stream.caplog.at_level(level, logger="bdbox"),
        console.log_stdout_stderr(),
    ):
        getattr(sys, stream_attr).write("no newline at end")
    records = log_stream.records_level(level)
    assert len(records) == 1
    assert records[0].message == "no newline at end"


def test_log_stdout_stderr_restores_on_exception() -> None:
    class CustomError(Exception):
        pass

    original_stdout, original_stderr = sys.stdout, sys.stderr
    with suppress(CustomError), console.log_stdout_stderr():
        raise CustomError
    assert sys.stdout is original_stdout
    assert sys.stderr is original_stderr


@pytest.mark.parametrize(
    ("verbose", "expected_level", "expected_reset"),
    [
        pytest.param(0, logging.INFO, False, id="verbose-0-info"),
        pytest.param(1, logging.DEBUG, True, id="verbose-1-debug"),
        pytest.param(2, LogLevel.TRACE, True, id="verbose-2-trace"),
    ],
)
def test_console_verbosity_level(
    verbose: int,
    expected_level: int,
    *,
    expected_reset: bool,
) -> None:
    with patch.object(console, "reset", wraps=console.reset) as mock_reset:
        console.configure(verbose=verbose)
    if expected_reset:
        mock_reset.assert_called_once_with()
    else:
        mock_reset.assert_not_called()
    assert console.terminal_output is not None
    assert console.terminal_output.level == expected_level


def test_add_remove_web_output() -> None:
    console.add_web_output(1138, io.StringIO(), width=80)
    handler = console.web_outputs[1138].handler
    assert handler in logging.getLogger().handlers
    console.remove_web_output(1138)
    assert handler not in logging.getLogger().handlers
    assert not console.web_outputs
    console.remove_web_output(2187)
    assert not console.web_outputs


def test_add_web_output_existing_updates_width() -> None:
    stream = io.StringIO()
    console.add_web_output(1138, stream, width=80)
    handler = console.web_outputs[1138].handler
    console.add_web_output(1138, stream, width=120)
    assert console.web_outputs[1138].handler is handler
    assert console.web_outputs[1138].console.width == 120


def test_activity_indicator_nontty_propagates_exception() -> None:

    class CustomError(Exception):
        pass

    with pytest.raises(CustomError), console.activity_indicator():
        raise CustomError
