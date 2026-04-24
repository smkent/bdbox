"""OCP CAD Viewer management tests."""

from __future__ import annotations

import random
import sys
import time
import webbrowser
from collections.abc import Callable, Sequence
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import psutil
import pytest

import bdbox.viewer as viewer_module
from bdbox.__main__ import main
from bdbox.runner.watcher import ModelWatcher
from bdbox.viewer import ViewerManager

from .utils import MockOcpVscode, Models

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from .utils import MockOcpVscode


ExecMain = Callable[..., None]


@pytest.fixture
def exec_main(monkeypatch: pytest.MonkeyPatch) -> ExecMain:
    def wrapper(*args: str) -> None:
        monkeypatch.setattr(sys, "argv", ["bdbox", *args])
        is_viewer = "viewer" in args[:1]
        with pytest.raises(SystemExit) if is_viewer else nullcontext():
            main()

    return wrapper


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
    with patch.object(viewer_module.subprocess, "Popen") as mocked:
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
        self.processes[pid] = (proc := MagicMock(pid=pid))
        return proc

    def assert_launched(self) -> None:
        self.mock_popen.assert_called_once_with(
            [sys.executable, "-m", "ocp_vscode"], start_new_session=True
        )

    def assert_not_launched(self) -> None:
        self.mock_popen.assert_not_called()

    def assert_terminated(self, pid: int | None = None) -> None:
        if not pid:
            self.mock_terminate.assert_called_once()
            return
        assert pid in self.processes
        self.mock_terminate.assert_called_once_with(
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
        "run",
        autospec=True,
        side_effect=lambda self: self.runner(),
    ) as mocked:
        yield mocked


@pytest.fixture(
    params=(
        pytest.param(True, id="watch"),
        pytest.param(False, id="no_watch"),
    )
)
def watch_args(
    request: pytest.FixtureRequest, mock_watch_run: MagicMock
) -> Iterator[Sequence[str]]:
    watch_enabled = bool(request.param)
    yield [] if watch_enabled else ["--no-watch"]
    if watch_enabled:
        mock_watch_run.assert_called_once()
    else:
        mock_watch_run.assert_not_called()


@pytest.mark.usefixtures("mock_net_connections_denied")
def test_start_running_process_url_fallback_on_access_denied(
    ps_mock: PSMock,
    mock_urlopen: MagicMock,
    model: Path,
    watch_args: Sequence[str],
    exec_main: ExecMain,
) -> None:
    """When net_connections raises AccessDenied, falls back to URL probe."""
    with ps_mock():
        exec_main(str(model), "view", *watch_args)
    mock_urlopen.assert_called_once_with(ps_mock.viewer_url)


@pytest.mark.usefixtures("mock_net_connections_denied")
def test_start_running_process_returns_none_when_all_attempts_fail(
    ps_mock: PSMock, mock_urlopen: MagicMock, model: Path, exec_main: ExecMain
) -> None:
    """AccessDenied + unreachable URL → running_process returns None."""

    class TempError(Exception):
        pass

    mock_urlopen.side_effect = [URLError("refused"), TempError]
    with ps_mock(launches=True), pytest.raises((TempError, SystemExit)):
        exec_main(str(model), "view", "--no-watch")
    assert mock_urlopen.call_count == 2
    mock_urlopen.assert_called_with(ps_mock.viewer_url)


@pytest.mark.parametrize(
    "restart",
    [pytest.param(True, id="restart"), pytest.param(False, id="no_restart")],
)
@pytest.mark.usefixtures("mock_net_connections_denied")
def test_start_running_without_pid(
    ps_mock: PSMock,
    capsys: pytest.CaptureFixture[str],
    mock_ocp_vscode: MockOcpVscode,
    model: Path,
    watch_args: Sequence[str],
    exec_main: ExecMain,
    *,
    restart: bool,
) -> None:
    """start() prints already-running (no PID) and skips relaunch."""
    with (
        ps_mock(),
        patch.object(mock_ocp_vscode.comms, "set_port") as mock_set_port,
    ):
        exec_main(
            str(model),
            "view",
            "--restart-viewer",
            "--no-open-browser",
            *watch_args,
        )

    mock_set_port.assert_called_once_with(ps_mock.ocp_port)
    assert "running" in capsys.readouterr().out


@pytest.mark.usefixtures("mock_net_connections_denied")
def test_stop_running_without_pid(
    ps_mock: PSMock, capsys: pytest.CaptureFixture[str], exec_main: ExecMain
) -> None:
    """stop() prints a message and skips termination without a PID."""
    with ps_mock():
        exec_main("viewer", "stop")
    assert "cannot" in capsys.readouterr().out.lower()


@pytest.mark.usefixtures("mock_net_connections_denied")
def test_status_running_without_pid(
    ps_mock: PSMock, capsys: pytest.CaptureFixture[str], exec_main: ExecMain
) -> None:
    """status() shows URL but omits PID when process info is unavailable."""
    with ps_mock():
        exec_main("viewer", "status")
    out = capsys.readouterr().out
    assert "localhost" in out
    assert "None" not in out


def test_start_launches(ps_mock: PSMock, exec_main: ExecMain) -> None:
    ps_mock.add_connection(pid=1138, port=8)
    with ps_mock(launches=True):
        exec_main("viewer", "start", "--no-open-browser")


def test_start_already_running_skips_subprocess(
    ps_mock: PSMock, exec_main: ExecMain
) -> None:
    ps_mock.add_connection(pid=1138)
    ps_mock.add_connection(port=ps_mock.ocp_port - 1, pid=4002)
    with ps_mock(launches=False):
        exec_main("viewer", "start", "--no-open-browser")


def test_start_restart_terminates_old_process_and_relaunches(
    ps_mock: PSMock, exec_main: ExecMain
) -> None:
    conn = ps_mock.add_connection(pid=1138)
    with ps_mock(launches=True, terminates=True):
        exec_main("viewer", "start", "--restart", "--no-open-browser")
    ps_mock.assert_terminated(conn.pid)


def test_start_opens_browser(ps_mock: PSMock, exec_main: ExecMain) -> None:
    class TempError(Exception):
        pass

    ps_mock.mock_browser_open.side_effect = TempError
    with ps_mock(launches=True, opens_browser=True), pytest.raises(TempError):
        exec_main("viewer", "start")


def test_start_skips_browser_when_disabled(
    ps_mock: PSMock, exec_main: ExecMain
) -> None:
    class TempError(Exception):
        pass

    ps_mock.mock_browser_open.side_effect = TempError
    with ps_mock(launches=True):
        exec_main("viewer", "start", "--no-open-browser")


def test_start_initializes_port_when_freshly_launched(
    ps_mock: PSMock, mock_ocp_vscode: MockOcpVscode, exec_main: ExecMain
) -> None:
    with (
        ps_mock(launches=True),
        patch.object(mock_ocp_vscode.comms, "set_port") as mock_set_port,
    ):
        exec_main("viewer", "start", "--no-open-browser")
    mock_set_port.assert_called_once_with(ps_mock.ocp_port)


def test_start_initializes_port_when_already_running(
    ps_mock: PSMock, mock_ocp_vscode: MockOcpVscode, exec_main: ExecMain
) -> None:
    ps_mock.add_connection(pid=1138)
    with (
        ps_mock(launches=False),
        patch.object(mock_ocp_vscode.comms, "set_port") as mock_set_port,
    ):
        exec_main("viewer", "start", "--no-open-browser")
    mock_set_port.assert_called_once_with(ps_mock.ocp_port)


def test_start_skips_wait_when_not_opening_browser(
    ps_mock: PSMock, exec_main: ExecMain
) -> None:
    with ps_mock(launches=True), patch.object(time, "sleep") as mock_sleep:
        exec_main("viewer", "start", "--no-open-browser")
    mock_sleep.assert_not_called()


def test_start_open_browser(ps_mock: PSMock, exec_main: ExecMain) -> None:
    with (
        ps_mock(launches=True, opens_browser=True),
        patch.object(time, "sleep") as mock_sleep,
    ):
        exec_main("viewer", "start")
    mock_sleep.assert_not_called()


def test_start_open_browser_wait(ps_mock: PSMock, exec_main: ExecMain) -> None:
    responses = [{}, {}, {"up": True}]
    ps_mock.mock_send_command.side_effect = lambda cmd: responses.pop(0)
    with (
        ps_mock(launches=True, opens_browser=True),
        patch.object(time, "sleep") as mock_sleep,
    ):
        exec_main("viewer", "start")
    assert mock_sleep.call_count == 2


def test_start_open_browser_wait_timeout(
    ps_mock: PSMock, capsys: pytest.CaptureFixture[str], exec_main: ExecMain
) -> None:
    ps_mock.mock_send_command.side_effect = lambda cmd: {}
    with (
        ps_mock(launches=True, opens_browser=True),
        patch.object(time, "sleep") as mock_sleep,
    ):
        exec_main("viewer", "start")
    assert mock_sleep.call_count == 120
    assert "Warning" in capsys.readouterr().out


def test_start_viewer_timeout(
    ps_mock: PSMock, mock_urlopen: MagicMock, exec_main: ExecMain
) -> None:
    mock_urlopen.side_effect = URLError("refused")
    ps_mock.mock_send_command.side_effect = lambda cmd: {}
    with (
        ps_mock(launches=True, opens_browser=False),
        patch.object(time, "sleep") as mock_sleep,
        pytest.raises(RuntimeError, match="failed to start"),
    ):
        exec_main("viewer", "start")
    assert mock_sleep.call_count == 100


def test_stop_terminates_running_process(
    ps_mock: PSMock, exec_main: ExecMain
) -> None:
    conn = ps_mock.add_connection(pid=1138)
    with ps_mock(launches=False, terminates=True):
        exec_main("viewer", "stop")
    ps_mock.assert_terminated(conn.pid)


def test_stop_when_not_running(
    ps_mock: PSMock, capsys: pytest.CaptureFixture[str], exec_main: ExecMain
) -> None:
    with ps_mock(launches=False):
        exec_main("viewer", "stop")
    assert "not running" in capsys.readouterr().out


def test_status_running_shows_url_and_pid(
    ps_mock: PSMock, capsys: pytest.CaptureFixture[str], exec_main: ExecMain
) -> None:
    conn = ps_mock.add_connection(pid=1138)
    with ps_mock(launches=False):
        exec_main("viewer", "status")
    out = capsys.readouterr().out
    assert str(conn.pid) in out
    assert "localhost" in out


def test_status_not_running(
    ps_mock: PSMock, capsys: pytest.CaptureFixture[str], exec_main: ExecMain
) -> None:
    with ps_mock(launches=False):
        exec_main("viewer", "status")
    assert "not running" in capsys.readouterr().out


@pytest.mark.usefixtures("harness_mode")
def test_model_view_starts_viewer(
    model: Path, watch_args: Sequence[str], exec_main: ExecMain
) -> None:
    with patch.object(ViewerManager, "start") as mock_start:
        exec_main(str(model), "view", *watch_args)
    mock_start.assert_called_once()


@pytest.mark.usefixtures("harness_mode")
def test_model_view_skips_viewer_when_disabled(
    model: Path, watch_args: Sequence[str], exec_main: ExecMain
) -> None:
    with patch.object(ViewerManager, "start") as mock_start:
        exec_main(str(model), "view", "--no-start-viewer", *watch_args)
    mock_start.assert_not_called()


@pytest.mark.usefixtures("harness_mode")
def test_model_view_passes_flags_to_viewer(
    model: Path, watch_args: Sequence[str], exec_main: ExecMain
) -> None:
    def check_args(self: ViewerManager) -> None:
        assert self.restart is True
        assert self.open_browser is False

    with patch.object(
        ViewerManager, "start", autospec=True, side_effect=check_args
    ) as mock_start:
        exec_main(
            str(model),
            "view",
            "--restart-viewer",
            "--no-open-browser",
            *watch_args,
        )
    mock_start.assert_called_once()


def test_viewer_start_open_browser(
    ps_mock: PSMock, exec_main: ExecMain
) -> None:
    with (
        ps_mock(launches=True, opens_browser=True),
        patch.object(time, "sleep") as mock_sleep,
    ):
        exec_main("viewer", "start")
    mock_sleep.assert_not_called()


def test_viewer_start_no_browser(ps_mock: PSMock, exec_main: ExecMain) -> None:
    with ps_mock(launches=True), patch.object(time, "sleep") as mock_sleep:
        exec_main("viewer", "start", "--no-open-browser")
    mock_sleep.assert_not_called()


def test_viewer_stop(ps_mock: PSMock, exec_main: ExecMain) -> None:
    conn = ps_mock.add_connection(pid=1138)
    with ps_mock(launches=False, terminates=True):
        exec_main("viewer", "stop")
    ps_mock.assert_terminated(conn.pid)


def test_viewer_status(
    ps_mock: PSMock, capsys: pytest.CaptureFixture[str], exec_main: ExecMain
) -> None:
    ps_mock.add_connection(pid=1138)
    with ps_mock(launches=False):
        exec_main("viewer", "status")
    assert "running" in capsys.readouterr().out
