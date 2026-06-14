"""UI server backend management."""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from uvicorn import Config, Server

from bdbox.console import log
from bdbox.dispatch import Event, Service, Thread
from bdbox.errors import UsageError

from .app import ViewServerApp

if TYPE_CHECKING:
    from bdbox.view.state import ViewState


@dataclass
class UvicornServer(Server):
    config: Config
    ready: Event = field(
        default_factory=lambda: Event(name="UvicornServer.ready")
    )

    def __post_init__(self) -> None:
        super().__init__(config=self.config)

    async def startup(self, sockets: Any = None) -> None:
        try:
            await super().startup(sockets=sockets)
        finally:
            self.ready.set()


@dataclass
class ViewServer(Service):
    app: ViewServerApp = field(init=False)
    view_state: ViewState
    port: int = 4040
    viewer_port: int = 3939
    open_browser: bool = True

    _STARTUP_TIMEOUT: ClassVar[float] = 10.0

    uvicorn_server: UvicornServer = field(init=False, repr=False)
    thread: Thread = field(init=False, repr=False)

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"

    def __post_init__(self) -> None:
        self.app = ViewServerApp(
            view_state=self.view_state, viewer_port=self.viewer_port
        )
        self.uvicorn_server = UvicornServer(
            Config(
                app=self.app,
                host="localhost",
                port=self.port,
                log_level="error",
                ws="websockets-sansio",
            )
        )
        self.thread = Thread(
            target=self.uvicorn_server.run, name="ui-server", daemon=True
        )
        super().__post_init__()

    def start(self) -> None:
        self.thread.start()

    def ready_wait(self) -> None:
        self.uvicorn_server.ready.wait(timeout=self._STARTUP_TIMEOUT)
        if not self.uvicorn_server.started:
            raise UsageError(
                "The view server failed to start."
                " Is another `view` instance already running?"
            )
        if self.port == 0:
            self.port = (
                self.uvicorn_server.servers[0].sockets[0].getsockname()[1]
            )
        log.info(f"Server running: {self.url}")
        if self.open_browser:
            webbrowser.open_new_tab(self.url)

    def stop(self) -> None:
        if self.uvicorn_server:
            self.uvicorn_server.should_exit = True
