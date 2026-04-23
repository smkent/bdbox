"""OCP CAD Viewer process management."""

from __future__ import annotations

import subprocess
import sys
import time
import webbrowser
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, ClassVar
from urllib.error import URLError
from urllib.request import urlopen

import psutil


@dataclass
class _ViewerStub:
    """Returned when viewer is up but PID cannot be determined."""

    pid: int | None = None


@dataclass
class ViewerManager:
    """Manages the OCP CAD Viewer subprocess."""

    restart: bool = False
    open_browser: bool = True

    _POLL_INTERVAL: ClassVar[float] = 0.25
    _POLL_ATTEMPTS: ClassVar[int] = 100
    _BROWSER_POLL_ATTEMPTS: ClassVar[int] = (
        120  # 30 seconds at 0.25s intervals
    )

    @property
    def _port(self) -> int:
        try:
            from ocp_vscode.comms import CMD_PORT  # noqa: PLC0415

            return int(CMD_PORT)
        except ImportError:
            return 3939

    @property
    def url(self) -> str:
        return f"http://localhost:{self._port}/viewer"

    def running_process(self) -> Any:
        try:
            connections = psutil.net_connections()
        except psutil.AccessDenied:
            with suppress(URLError):
                urlopen(self.url).read()  # noqa: S310
                return _ViewerStub()
            return None
        return next(
            (
                psutil.Process(c.pid)
                for c in connections
                if c.laddr
                and c.laddr.port == self._port
                and c.pid
                and c.status.lower() == "listen"
            ),
            None,
        )

    def start(self) -> None:
        if proc := self.running_process():
            if not self.restart:
                pid_str = f" (PID {proc.pid})" if proc.pid else ""
                print(f"OCP viewer already running: {self.url}{pid_str}")  # noqa: T201
                self._init_port()
                return
            if proc.pid is None:
                print(  # noqa: T201
                    "OCP viewer running but PID unknown; skipping restart"
                )
                self._init_port()
                return
            print(f"Stopping OCP viewer (PID {proc.pid})")  # noqa: T201
            self._terminate(proc)
        print("Starting OCP viewer")  # noqa: T201
        subprocess.Popen(
            [sys.executable, "-m", "ocp_vscode"], start_new_session=True
        )
        for _ in range(self._POLL_ATTEMPTS):
            try:
                urlopen(self.url).read()  # noqa: S310
                break
            except URLError:
                time.sleep(self._POLL_INTERVAL)
        else:
            raise RuntimeError("OCP viewer failed to start")
        print(f"OCP viewer running: {self.url}")  # noqa: T201
        self._init_port()
        if self.open_browser:
            webbrowser.open_new_tab(self.url)
            self._wait_for_browser()

    def stop(self) -> None:
        if proc := self.running_process():
            if proc.pid is None:
                print("OCP viewer is running but PID is unknown; cannot stop")  # noqa: T201
                return
            print(f"Stopping OCP viewer (PID {proc.pid})")  # noqa: T201
            self._terminate(proc)
        else:
            print("OCP viewer is not running")  # noqa: T201

    def status(self) -> None:
        if proc := self.running_process():
            pid_str = f" (PID {proc.pid})" if proc.pid else ""
            print(f"OCP viewer running: {self.url}{pid_str}")  # noqa: T201
        else:
            print("OCP viewer is not running")  # noqa: T201

    def _terminate(self, proc: Any) -> None:
        proc.terminate()
        psutil.wait_procs([proc], timeout=2)

    def _init_port(self) -> None:
        """Pre-set port to skip find_and_set_port() on first show()."""
        from ocp_vscode.comms import set_port  # noqa: PLC0415

        set_port(self._port)

    def _send_command(self, cmd: str) -> str:
        from ocp_vscode.comms import send_command  # noqa: PLC0415

        return send_command(cmd)

    def _wait_for_browser(self) -> None:
        """Poll until the browser WebSocket has registered with the viewer."""
        for _ in range(self._BROWSER_POLL_ATTEMPTS):
            with suppress(Exception):
                if self._send_command("status"):
                    return
            time.sleep(self._POLL_INTERVAL)
        print("Warning: browser did not connect within timeout")  # noqa: T201
