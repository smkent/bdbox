"""UI server backend management."""

from __future__ import annotations

import time
import webbrowser
from dataclasses import dataclass, field
from threading import Thread
from typing import TYPE_CHECKING, ClassVar
from urllib.error import URLError
from urllib.request import urlopen

from uvicorn import Config, Server

from .app import App

if TYPE_CHECKING:
    from .context import Context


@dataclass
class ServerManager:
    context: Context
    port: int = 4040
    open_browser: bool = True

    _POLL_INTERVAL: ClassVar[float] = 0.25
    _POLL_ATTEMPTS: ClassVar[int] = 40
    _STOP_TIMEOUT: ClassVar[float] = 5.0

    server: Server | None = field(default=None, init=False, repr=False)
    thread: Thread | None = field(default=None, init=False, repr=False)

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"

    def start(self) -> ServerManager:
        app = App(self.context)
        self.server = Server(
            Config(
                app=app, host="localhost", port=self.port, log_level="error"
            )
        )
        self.thread = Thread(target=self.server.run, daemon=True)
        self.thread.start()
        for _ in range(self._POLL_ATTEMPTS):
            try:
                urlopen(self.url).read()  # noqa: S310
                break
            except URLError:
                time.sleep(self._POLL_INTERVAL)
        else:
            raise RuntimeError("bdbox server failed to start")
        print(f"bdbox server running: {self.url}")  # noqa: T201
        if self.open_browser:
            webbrowser.open_new_tab(self.url)
        return self

    def stop(self) -> None:
        if self.server:
            self.server.should_exit = True
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=self._STOP_TIMEOUT)
