"""OCP CAD Viewer process management."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.error import URLError
from urllib.request import urlopen

import psutil

from bdbox.console import log
from bdbox.dispatch import Service

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class _ViewerStub:
    """Returned when viewer is up but PID cannot be determined."""

    pid: int | None = None


@dataclass
class ViewerManager(Service):
    """Manages the OCP CAD Viewer subprocess."""

    ocp_vscode_args: ClassVar[Sequence[str]] = (
        "--theme=dark",
        "--reset_camera=keep",
    )

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
            if proc.pid is None:
                log.warning(
                    "OCP CAD Viewer is already running, but PID unknown"
                )
            else:
                log.debug(f"Stopping (PID {proc.pid})")
                self._terminate(proc)
        log.debug("Starting OCP CAD Viewer")
        popen_kwargs: dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
            subprocess.Popen(  # noqa: S603
                [sys.executable, "-m", "ocp_vscode", *self.ocp_vscode_args],
                **popen_kwargs,
            )

    def ready_wait(self) -> None:
        for _ in range(self._POLL_ATTEMPTS):
            try:
                urlopen(self.url).read()  # noqa: S310
                break
            except URLError:
                time.sleep(self._POLL_INTERVAL)
        else:
            raise RuntimeError("OCP CAD Viewer failed to start")
        log.debug(f"OCP CAD Viewer running on port {self._port}")
        self._init_port()

    def stop(self) -> None:
        if proc := self.running_process():
            if proc.pid is None:
                log.warning(
                    "OCP CAD Viewer running but PID unknown; cannot stop"
                )
                return
            log.debug(f"Stopping OCP CAD Viewer (PID {proc.pid})")
            self._terminate(proc)
        else:
            log.debug("OCP CAD Viewer not running")

    def _terminate(self, proc: Any) -> None:
        proc.terminate()
        psutil.wait_procs([proc], timeout=2)

    def _init_port(self) -> None:
        """Pre-set port to skip find_and_set_port() on first show()."""
        from ocp_vscode.comms import set_port  # noqa: PLC0415

        set_port(self._port)
