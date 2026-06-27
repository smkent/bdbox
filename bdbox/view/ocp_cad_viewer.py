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
from bdbox.dispatch import Service, Thread

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence


@dataclass
class OCPCADViewer(Service):
    """Manages the OCP CAD Viewer subprocess."""

    client_registered: Callable[[], None] = field(repr=False)
    process: subprocess.Popen[str] | None = field(default=None, init=False)
    ocp_vscode_args: ClassVar[Sequence[str]] = ("--theme=dark",)
    port: int = 0

    _POLL_INTERVAL: ClassVar[float] = 0.25
    _POLL_ATTEMPTS: ClassVar[int] = 100

    def __post_init__(self) -> None:
        if self.port == 0:
            self._set_port()
        super().__post_init__()

    @cached_property
    def popen_kwargs(self) -> Mapping[str, Any]:
        popen_kwargs: dict[str, Any] = {
            "text": True,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
        return popen_kwargs

    def start(self) -> None:
        cmd = [
            sys.executable,
            "-u",
            "-m",
            "ocp_vscode",
            f"--port={self.port}",
            *self.ocp_vscode_args,
        ]
        log.debug("Starting OCP CAD Viewer")
        log.trace("Running: %s", " ".join(cmd))
        self.process = subprocess.Popen(cmd, **self.popen_kwargs)  # noqa: S603

        def _watch() -> None:
            if not self.process or not self.process.stdout:
                return
            for line in self.process.stdout:
                if "Browser as viewer client registered" in line:
                    log.debug("OCP CAD Viewer browser client connected")
                    self.client_registered()

        Thread(
            target=_watch, name="viewer client connect", daemon=True
        ).start()

    def _configure(self) -> None:
        from ocp_vscode.config import (  # noqa: PLC0415
            Camera,
            reset_defaults,
            set_defaults,
        )

        reset_defaults()
        set_defaults(reset_camera=Camera.KEEP)

    def _set_port(self) -> None:
        try:
            from ocp_vscode.comms import CMD_PORT  # noqa: PLC0415

            self.port = int(CMD_PORT)
        except ImportError:
            self.port = 3939
        from ocp_vscode.comms import set_port  # noqa: PLC0415

        set_port(self.port)

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}/viewer"

    def ready_wait(self) -> None:
        for _ in range(self._POLL_ATTEMPTS):
            try:
                urlopen(self.url).read()  # noqa: S310
                break
            except URLError:
                time.sleep(self._POLL_INTERVAL)
        else:
            raise RuntimeError("OCP CAD Viewer failed to start")
        log.debug(f"OCP CAD Viewer running on port {self.port}")
        self._configure()

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
