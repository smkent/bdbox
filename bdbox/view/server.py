"""UI server backend management."""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass, field
from threading import Event, Thread
from typing import TYPE_CHECKING, Any, ClassVar

from uvicorn import Config, Server

from bdbox.console import log
from bdbox.errors import UsageError

from .app import App

if TYPE_CHECKING:
    from .state import ViewState


class _Server(Server):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.startup_complete = Event()

    async def startup(self, sockets: Any = None) -> None:
        try:
            await super().startup(sockets=sockets)
        finally:
            self.startup_complete.set()


@dataclass
class ServerManager:
    view_state: ViewState
    port: int = 4040
    open_browser: bool = True

    _STARTUP_TIMEOUT: ClassVar[float] = 10.0
    _STOP_TIMEOUT: ClassVar[float] = 5.0

    server: _Server | None = field(default=None, init=False, repr=False)
    thread: Thread | None = field(default=None, init=False, repr=False)

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"

    def start(self) -> ServerManager:
        app = App(self.view_state)
        self.server = _Server(
            Config(
                app=app, host="localhost", port=self.port, log_level="error"
            )
        )
        self.thread = Thread(target=self.server.run, daemon=True)
        self.thread.start()
        self.server.startup_complete.wait(timeout=self._STARTUP_TIMEOUT)
        if not self.server.started:
            raise UsageError(
                "The view server failed to start."
                " Is another `view` instance already running?"
            )
        log.info(f"Server running: {self.url}")
        if self.open_browser:
            webbrowser.open_new_tab(self.url)
        return self

    def stop(self) -> None:
        if self.server:
            self.server.should_exit = True
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=self._STOP_TIMEOUT)
