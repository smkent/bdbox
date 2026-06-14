"""OCP CAD Viewer process management."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.error import URLError
from urllib.request import urlopen

from bdbox.console import log
from bdbox.dispatch import Service

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


@dataclass
class ViewerManager(Service):
    """Manages the OCP CAD Viewer subprocess."""

    process: subprocess.Popen[str] | None = field(default=None, init=False)
    ocp_vscode_args: ClassVar[Sequence[str]] = (
        "--theme=dark",
        "--reset_camera=keep",
    )

    _POLL_INTERVAL: ClassVar[float] = 0.25
    _POLL_ATTEMPTS: ClassVar[int] = 100

    @cached_property
    def popen_kwargs(self) -> Mapping[str, Any]:
        popen_kwargs: dict[str, Any] = {
            "text": True,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
        return popen_kwargs

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

    def start(self) -> None:
        log.debug("Starting OCP CAD Viewer")
        self.process = subprocess.Popen(  # noqa: S603
            [sys.executable, "-m", "ocp_vscode", *self.ocp_vscode_args],
            **self.popen_kwargs,
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

        # Set port to skip find_and_set_port() on first show().
        from ocp_vscode.comms import set_port  # noqa: PLC0415

        set_port(self._port)

    def stop(self) -> None:
        if not self.process:
            return
        log.debug("Stopping OCP CAD Viewer")
        self.process.terminate()
        try:
            self.process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            log.debug("Terminating OCP CAD Viewer")
            self.process.kill()
            self.process.wait()
