"""OCP CAD Viewer process management."""

from __future__ import annotations

import os
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

from bdbox.console import log


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
    def port(self) -> int:
        return self._port

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
                log.info(f"Already running on port {self._port}{pid_str}")
                self._init_port()
                return
            if proc.pid is None:
                log.warning("Running but PID unknown; skipping restart")
                self._init_port()
                return
            log.info(f"Stopping (PID {proc.pid})")
            self._terminate(proc)
        log.info("Starting OCP CAD Viewer")
        popen_kwargs: dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
        subprocess.Popen([sys.executable, "-m", "ocp_vscode"], **popen_kwargs)
        for _ in range(self._POLL_ATTEMPTS):
            try:
                urlopen(self.url).read()  # noqa: S310
                break
            except URLError:
                time.sleep(self._POLL_INTERVAL)
        else:
            raise RuntimeError("OCP viewer failed to start")
        log.info(f"Running on port {self._port}")
        self._init_port()
        if self.open_browser:
            webbrowser.open_new_tab(self.url)
            self._wait_for_browser()

    def stop(self) -> None:
        if proc := self.running_process():
            if proc.pid is None:
                log.warning("Running but PID unknown; cannot stop")
                return
            log.info(f"Stopping (PID {proc.pid})")
            self._terminate(proc)
        else:
            log.info("Not running")

    def status(self) -> None:
        if proc := self.running_process():
            pid_str = f" (PID {proc.pid})" if proc.pid else ""
            log.info(f"Running: {self.url}{pid_str}")
        else:
            log.info("Not running")

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
        log.warning("Browser did not connect within timeout")
