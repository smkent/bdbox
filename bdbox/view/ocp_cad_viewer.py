"""OCP CAD Viewer process management."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.error import URLError
from urllib.request import urlopen

from bdbox.console import log
from bdbox.dispatch import ListenService, Thread

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence


@dataclass
class OCPCADViewer(ListenService):
    """Manages the OCP CAD Viewer subprocess."""

    client_registered: Callable[[], None] = field(repr=False)
    process: subprocess.Popen[str] | None = field(default=None, init=False)
    ocp_viewer_args: ClassVar[Sequence[str]] = ("--theme=dark",)

    _POLL_INTERVAL: ClassVar[float] = 0.25
    _POLL_ATTEMPTS: ClassVar[int] = 100
    _OUTPUT_LINES: ClassVar[int] = 20

    _output: deque[str] = field(
        default_factory=lambda: deque(maxlen=OCPCADViewer._OUTPUT_LINES),
        init=False,
        repr=False,
    )
    _watcher: Thread | None = field(default=None, init=False, repr=False)

    @cached_property
    def popen_kwargs(self) -> Mapping[str, Any]:
        popen_kwargs: dict[str, Any] = {
            "text": True,
            "stdout": subprocess.PIPE,
            # Merged into stdout so a viewer that fails to start can say
            # why, rather than only timing out in `ready_wait`.
            "stderr": subprocess.STDOUT,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
        return popen_kwargs

    def start(self) -> None:
        from ocp_viewer.comms import set_port  # noqa: PLC0415

        set_port(self.port)

        cmd = [
            sys.executable,
            "-u",
            "-m",
            "ocp_viewer",
            f"--port={self.port}",
            *self.ocp_viewer_args,
        ]
        log.debug("Starting OCP CAD Viewer")
        log.trace("Running: %s", " ".join(cmd))
        self.process = subprocess.Popen(cmd, **self.popen_kwargs)  # noqa: S603

        def _watch() -> None:
            if not self.process or not self.process.stdout:
                return
            for line in self.process.stdout:
                self._output.append(line.rstrip())
                if "Browser as viewer client registered" in line:
                    log.debug("OCP CAD Viewer browser client connected")
                    self.client_registered()

        self._watcher = Thread(
            target=_watch, name="viewer client connect", daemon=True
        )
        self._watcher.start()

    def _configure(self) -> None:
        from ocp_viewer.config import (  # noqa: PLC0415
            Camera,
            reset_defaults,
            set_defaults,
        )

        reset_defaults()
        set_defaults(reset_camera=Camera.KEEP)

    @property
    def url(self) -> str:
        return f"{self.base_url}/viewer"

    def _exited_error(self) -> RuntimeError:
        """Describe a viewer process that exited, quoting its own output."""
        if self._watcher:
            # Let the watcher drain the pipe so the message is complete.
            self._watcher.join(timeout=self._POLL_INTERVAL)
        returncode = self.process.returncode if self.process else None
        message = f"OCP CAD Viewer exited with status {returncode}"
        if output := "\n".join(self._output).strip():
            message = f"{message}:\n{output}"
        return RuntimeError(message)

    def ready_wait(self) -> None:
        for _ in range(self._POLL_ATTEMPTS):
            if self.process and self.process.poll() is not None:
                raise self._exited_error()
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
