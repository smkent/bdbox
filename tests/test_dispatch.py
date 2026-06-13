from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

import bdbox.view.server as server_module
from bdbox.console import LogLevel
from bdbox.dispatch import Event, Thread, dispatch
from bdbox.view.state import ViewState
from bdbox.viewer import ViewerManager
from tests.utils import ExecMain, Models, ThreadExceptions

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@dataclass
class ExitOnWaitEvent(Event):
    def wait(self, timeout: float | None = None) -> bool:
        dispatch.exit.set()
        return super().wait(timeout)


@pytest.fixture(autouse=True)
def mock_watcher_event() -> Iterator[None]:
    original = ViewState.__init__

    def _mock(self: ViewState, *args: Any, **kwargs: Any) -> None:
        original(self, *args, **kwargs)
        self.rerender_event = ExitOnWaitEvent(name="mock_rerender_exit")

    with patch.object(ViewState, "__init__", _mock):
        yield


@pytest.fixture(autouse=True)
def mock_viewer_start() -> Iterator[MagicMock]:
    with patch.object(ViewerManager, "start") as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_server_start() -> Iterator[MagicMock]:
    with patch.object(
        server_module.ServerManager, "start", autospec=True
    ) as mocked:
        yield mocked


@pytest.fixture(
    params=[
        pytest.param(Models.MODEL_EXPORT, id="Model"),
        pytest.param(Models.PARAMS_EXPORT, id="Params"),
    ]
)
def model(request: pytest.FixtureRequest) -> Path:
    return request.param


def test_dispatch(
    exec_main: ExecMain,
    mock_viewer_start: MagicMock,
    mock_server_start: MagicMock,
    model: Path,
) -> None:
    exec_main(str(model), "view")
    mock_viewer_start.assert_called_once()
    mock_server_start.assert_called_once()


def test_dispatch_prints_trace_logs(
    caplog: pytest.LogCaptureFixture,
    exec_main: ExecMain,
    mock_viewer_start: MagicMock,
    mock_server_start: MagicMock,
    model: Path,
) -> None:
    with caplog.at_level(LogLevel.TRACE, logger="bdbox"):
        exec_main(str(model), "view", "-vv")
    assert any(r.levelno == LogLevel.TRACE for r in caplog.records)
    mock_viewer_start.assert_called_once()
    mock_server_start.assert_called_once()


def test_dispatch_thread(
    thread_exceptions: ThreadExceptions,
    exec_main: ExecMain,
    mock_viewer_start: MagicMock,
    mock_server_start: MagicMock,
    model: Path,
) -> None:
    class TestError(Exception):
        pass

    def _run() -> None:
        raise TestError("Thread exception")

    with thread_exceptions.raises(TestError):
        Thread(target=_run).start()
        exec_main(str(model), "view")
    mock_viewer_start.assert_called_once()
    mock_server_start.assert_called_once()
