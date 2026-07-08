"""UI server backend management."""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from uvicorn import Config, Server

from bdbox.console import log
from bdbox.dispatch import Event, ListenService, Thread
from bdbox.errors import UsageError

from .app import UIApp

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
class UIServer(ListenService):
    app: UIApp = field(init=False)
    view_state: ViewState
    ocp_cad_viewer_port: int = 3939
    open_browser: bool = True

    _STARTUP_TIMEOUT: ClassVar[float] = 10.0

    uvicorn_server: UvicornServer = field(init=False, repr=False)
    thread: Thread = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.app = UIApp(
            view_state=self.view_state,
            ocp_cad_viewer_port=self.ocp_cad_viewer_port,
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
        log.info(f"Server running: {self.base_url}")
        if self.open_browser:
            webbrowser.open_new_tab(self.base_url)

    def stop(self) -> None:
        if self.uvicorn_server:
            self.uvicorn_server.should_exit = True
