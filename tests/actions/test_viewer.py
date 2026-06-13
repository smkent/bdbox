"""OCP CAD Viewer management tests."""

from __future__ import annotations

import random
import subprocess
import sys
import webbrowser
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import psutil
import pytest

import bdbox.viewer as viewer_module
from bdbox.actions.view import ViewAction
from bdbox.runner.watcher import ModelWatcher
from bdbox.viewer import ViewerManager
from tests.utils import ExecMain, MockOcpVscode, Models

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path


pytestmark = pytest.mark.usefixtures("mock_server_start")


@pytest.fixture(
    params=[
        pytest.param(Models.MODEL_EXPORT, id="Model"),
        pytest.param(Models.PARAMS_EXPORT, id="Params"),
    ]
)
def model(request: pytest.FixtureRequest) -> Path:
    return request.param


@pytest.fixture(autouse=True)
def mock_urlopen() -> Iterator[MagicMock]:
    with patch.object(viewer_module, "urlopen") as mocked:
        yield mocked


@pytest.fixture
def mock_popen() -> Iterator[MagicMock]:
    with patch.object(subprocess, "Popen") as mocked:
        yield mocked


@pytest.fixture
def mock_net_connections() -> Iterator[MagicMock]:
    with patch.object(psutil, "net_connections") as mocked:
        yield mocked


@pytest.fixture
def mock_net_connections_denied(
    mock_net_connections: MagicMock,
) -> Iterator[MagicMock]:
    mock_net_connections.side_effect = psutil.AccessDenied(0)
    return mock_net_connections


@pytest.fixture(autouse=True)
def mock_terminate() -> Iterator[MagicMock]:
    with patch.object(psutil, "wait_procs") as mock_wait_procs:
        yield mock_wait_procs


@pytest.fixture
def mock_send_command(mock_ocp_vscode: MockOcpVscode) -> Iterator[MagicMock]:
    with patch.object(
        mock_ocp_vscode.comms,
        "send_command",
        side_effect=lambda cmd: {"up": True},
    ) as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_browser_open() -> Iterator[MagicMock]:
    with patch.object(webbrowser, "open_new_tab") as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_view_action_on_model_render() -> Iterator[MagicMock]:
    @contextmanager
    def on_model_render() -> Iterator[None]:
        yield

    with patch.object(
        ViewAction, "on_model_render", side_effect=on_model_render
    ) as mocked:
        yield mocked


@pytest.fixture
def random_ocp_port() -> int:
    return random.randint(1000, 65000)  # noqa: S311


@dataclass
class PSMock:
    mock_ocp_vscode: MockOcpVscode
    mock_send_command: MagicMock
    mock_net_connections: MagicMock
    mock_terminate: MagicMock
    mock_popen: MagicMock
    mock_browser_open: MagicMock

    ocp_port: int = 3939
    connections: list[PSMock.Conn] = field(default_factory=list, init=False)
    processes: dict[int, MagicMock] = field(default_factory=dict, init=False)

    @dataclass
    class ConnLaddr:
        port: int

    @dataclass
    class Conn:
        laddr: PSMock.ConnLaddr
        pid: int
        status: str = "LISTEN"

    @contextmanager
    def __call__(
        self,
        connections: Sequence[MagicMock] = (),
        *,
        launches: bool = False,
        terminates: bool = False,
        opens_browser: bool = False,
    ) -> Iterator[Any]:
        self.mock_net_connections.return_value = (
            list(connections) or self.connections
        )

        try:
            with (
                patch.object(
                    self.mock_ocp_vscode.comms, "CMD_PORT", self.ocp_port
                ),
                patch.object(psutil, "Process", side_effect=self.add_process),
            ):
                yield
        finally:
            if opens_browser:
                self.mock_browser_open.assert_called_once_with(self.viewer_url)
            else:
                self.mock_browser_open.assert_not_called()
            if launches:
                self.assert_launched()
            else:
                self.assert_not_launched()
            if terminates:
                self.assert_terminated()
            else:
                self.assert_not_terminated()

    @property
    def viewer_url(self) -> str:
        return f"http://localhost:{self.ocp_port}/viewer"

    def add_connection(
        self, pid: int, port: int | None = None, status: str = "LISTEN"
    ) -> Conn:
        conn = self.Conn(
            laddr=self.ConnLaddr(port=port or self.ocp_port),
            pid=pid,
            status=status,
        )
        self.connections.append(conn)
        return conn

    def add_process(self, pid: int) -> MagicMock:
        self.processes[pid] = (proc := MagicMock(pid=pid, name="pid_mock"))
        return proc

    def assert_launched(self) -> None:
        self.mock_popen.assert_called_once_with(
            [
                sys.executable,
                "-m",
                "ocp_vscode",
                "--theme=dark",
                "--reset_camera=keep",
            ],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def assert_not_launched(self) -> None:
        self.mock_popen.assert_not_called()

    def assert_terminated(self, pid: int | None = None) -> None:
        if not pid:
            for pid in self.processes:
                self.mock_terminate.assert_called_with(
                    [self.processes[pid]], timeout=2
                )
            return
        assert pid in self.processes
        self.mock_terminate.assert_called_with(
            [self.processes[pid]], timeout=2
        )

    def assert_not_terminated(self) -> None:
        self.mock_terminate.assert_not_called()


@pytest.fixture
def ps_mock(
    mock_ocp_vscode: MockOcpVscode,
    mock_send_command: MagicMock,
    mock_net_connections: MagicMock,
    mock_terminate: MagicMock,
    mock_popen: MagicMock,
    mock_browser_open: MagicMock,
    random_ocp_port: int,
) -> PSMock:
    return PSMock(
        mock_ocp_vscode=mock_ocp_vscode,
        mock_send_command=mock_send_command,
        mock_net_connections=mock_net_connections,
        mock_terminate=mock_terminate,
        mock_popen=mock_popen,
        mock_browser_open=mock_browser_open,
        ocp_port=random_ocp_port,
    )


@pytest.fixture(autouse=True)
def mock_watch_run() -> Iterator[MagicMock]:
    with patch.object(
        ModelWatcher,
        "start",
        autospec=True,
        side_effect=lambda self: self.runner(),
    ) as mocked:
        yield mocked


@pytest.mark.usefixtures("mock_net_connections_denied")
def test_start_running_process_url_fallback_on_access_denied(
    ps_mock: PSMock,
    mock_urlopen: MagicMock,
    model: Path,
    exec_main: ExecMain,
) -> None:
    """When net_connections raises AccessDenied, falls back to URL probe."""
    with ps_mock(launches=True):
        exec_main(str(model), "view")
    assert mock_urlopen.call_count == 3
    mock_urlopen.assert_called_with(ps_mock.viewer_url)


@pytest.mark.usefixtures("mock_net_connections_denied")
def test_start_running_process_returns_none_when_all_attempts_fail(
    ps_mock: PSMock, mock_urlopen: MagicMock, model: Path, exec_main: ExecMain
) -> None:
    """AccessDenied + unreachable URL → running_process returns None."""

    class TempError(Exception):
        pass

    mock_urlopen.side_effect = [URLError("refused"), TempError]
    with ps_mock(launches=True), pytest.raises((TempError, SystemExit)):
        exec_main(str(model), "view", "--open-browser")
    assert mock_urlopen.call_count == 2
    mock_urlopen.assert_called_with(ps_mock.viewer_url)


@pytest.mark.usefixtures("mock_net_connections_denied")
def test_start_running_without_pid(
    ps_mock: PSMock,
    log: pytest.LogCaptureFixture,
    mock_ocp_vscode: MockOcpVscode,
    model: Path,
    exec_main: ExecMain,
) -> None:
    """start() warns if already running but PID can't be determined."""
    with (
        ps_mock(launches=True),
        patch.object(mock_ocp_vscode.comms, "set_port") as mock_set_port,
    ):
        exec_main(str(model), "view")

    mock_set_port.assert_called_once_with(ps_mock.ocp_port)
    assert "but PID unknown" in log.text


def test_model_view_restarts_already_running_viewer(
    ps_mock: PSMock, exec_main: ExecMain, model: Path
) -> None:
    conn = ps_mock.add_connection(pid=1138)
    with ps_mock(terminates=True, launches=True):
        exec_main(str(model), "view")
    ps_mock.assert_terminated(conn.pid)


def test_model_view_starts_viewer(
    model: Path, exec_main: ExecMain, mock_server_start: MagicMock
) -> None:
    with patch.object(ViewerManager, "start") as mock_viewer_start:
        exec_main(str(model), "view")
    mock_viewer_start.assert_called_once()
    mock_server_start.assert_called_once()


def test_model_view_without_model_does_not_start_viewer(
    exec_main: ExecMain, mock_server_start: MagicMock
) -> None:
    with (
        patch.object(ViewerManager, "start") as mock_viewer_start,
        pytest.raises(SystemExit),
    ):
        exec_main("view")
    mock_viewer_start.assert_not_called()
    mock_server_start.assert_not_called()


def test_model_view_passes_flags_to_server(
    model: Path,
    exec_main: ExecMain,
    mock_server_start: MagicMock,
) -> None:
    with patch.object(ViewerManager, "start"):
        exec_main(str(model), "view")
    mock_server_start.assert_called_once()
    server_instance = mock_server_start.call_args[0][0]
    assert server_instance.open_browser is False
