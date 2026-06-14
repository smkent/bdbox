"""View application."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import TYPE_CHECKING

from bdbox.view.server.server import ViewServer
from bdbox.view.state import ViewState
from bdbox.viewer import ViewerManager

if TYPE_CHECKING:
    from bdbox.model.parameters import Params
    from bdbox.protocol import ServerMessage


@dataclass
class ViewApp:
    """View model geometry in OCP CAD Viewer."""

    server_port: InitVar[int]
    model_class: InitVar[type[Params] | None] = None
    open_browser: InitVar[bool] = False

    view_state: ViewState = field(init=False)
    viewer: ViewerManager = field(default_factory=ViewerManager)
    view_server: ViewServer = field(init=False)

    def __post_init__(
        self,
        server_port: int,
        model_class: type[Params] | None,
        open_browser: bool,
    ) -> None:
        self.view_state = ViewState(model_class=model_class)
        self.view_server = ViewServer(
            port=server_port,
            view_state=self.view_state,
            viewer_port=self.viewer.port,
            open_browser=open_browser,
        )
        self.viewer.ready_wait()
        self.view_server.ready_wait()

    def enqueue(self, msg: ServerMessage) -> None:
        self.view_server.app.enqueue(msg)
