"""View application."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import TYPE_CHECKING

from bdbox.view.server import ServerManager
from bdbox.view.state import ViewState
from bdbox.viewer import ViewerManager

if TYPE_CHECKING:
    from bdbox.model.parameters import Params
    from bdbox.protocol import ServerMessage


@dataclass
class ViewManager:
    """View model geometry in OCP CAD Viewer."""

    server_port: InitVar[int]
    model_class: InitVar[type[Params] | None] = None
    open_browser: InitVar[bool] = False

    view_state: ViewState = field(init=False)
    viewer: ViewerManager = field(default_factory=ViewerManager)
    server_manager: ServerManager = field(init=False)

    def __post_init__(
        self,
        server_port: int,
        model_class: type[Params] | None,
        open_browser: bool,
    ) -> None:
        self.view_state = ViewState(model_class=model_class)
        self.server_manager = ServerManager(
            port=server_port,
            view_state=self.view_state,
            viewer_port=self.viewer.port,
            open_browser=open_browser,
        )
        self.viewer.ready_wait()
        self.server_manager.ready_wait()

    def enqueue(self, msg: ServerMessage) -> None:
        self.server_manager.app.enqueue(msg)
