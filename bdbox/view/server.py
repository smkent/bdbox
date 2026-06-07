"""UI server backend management."""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from uvicorn import Config, Server

from bdbox.console import log
from bdbox.dispatch import Event, Service, Thread
from bdbox.errors import UsageError

from .app import App

if TYPE_CHECKING:
    from .state import ViewState


@dataclass
class UIServer(Server):
    config: Config
    startup_complete: Event = field(
        default_factory=lambda: Event(name="server_startup_complete")
    )

    def __post_init__(self) -> None:
        super().__init__(config=self.config)

    async def startup(self, sockets: Any = None) -> None:
        try:
            await super().startup(sockets=sockets)
        finally:
            self.startup_complete.set()


@dataclass
class ServerManager(Service):
    view_state: ViewState
    port: int = 4040
    open_browser: bool = True

    _STARTUP_TIMEOUT: ClassVar[float] = 10.0
    _STOP_TIMEOUT: ClassVar[float] = 5.0

    server: UIServer | None = field(default=None, init=False, repr=False)
    thread: Thread | None = field(default=None, init=False, repr=False)

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"

    def start(self) -> None:
        app = App(self.view_state)
        self.server = UIServer(
            Config(
                app=app, host="localhost", port=self.port, log_level="error"
            )
        )
        self.thread = Thread(
            target=self.server.run, name="ui-server", daemon=True
        )
        self.thread.start()
        self.server.startup_complete.wait(timeout=self._STARTUP_TIMEOUT)
        if not self.server.started:
            raise UsageError(
                "The view server failed to start."
                " Is another `view` instance already running?"
            )
        if self.port == 0:
            self.port = self.server.servers[0].sockets[0].getsockname()[1]
        log.info(f"Server running: {self.url}")
        if self.open_browser:
            webbrowser.open_new_tab(self.url)

    def stop(self) -> None:
        if self.server:
            self.server.should_exit = True
