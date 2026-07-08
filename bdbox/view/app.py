"""View application."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import TYPE_CHECKING

from bdbox.view.ocp_cad_viewer import OCPCADViewer
from bdbox.view.state import ViewState
from bdbox.view.ui.server import UIServer

if TYPE_CHECKING:
    from bdbox.model.parameters import Params
    from bdbox.protocol import ServerMessage


@dataclass
class ViewApp:
    """View model geometry in OCP CAD Viewer."""

    server_port: InitVar[int]
    model_class: InitVar[type[Params] | None] = None
    open_browser: InitVar[bool] = False

    ocp_cad_viewer: OCPCADViewer = field(init=False)
    view_state: ViewState = field(init=False)
    ui_server: UIServer = field(init=False)

    def __post_init__(
        self,
        server_port: int,
        model_class: type[Params] | None,
        open_browser: bool,
    ) -> None:
        self.view_state = ViewState(model_class=model_class)
        self.ocp_cad_viewer = OCPCADViewer(self.view_state.show)
        self.ui_server = UIServer(
            listen_port=server_port,
            view_state=self.view_state,
            ocp_cad_viewer_port=self.ocp_cad_viewer.port,
            open_browser=open_browser,
        )
        self.ocp_cad_viewer.ready_wait()
        self.ui_server.ready_wait()

    def enqueue(self, msg: ServerMessage) -> None:
        self.ui_server.app.enqueue(msg)
