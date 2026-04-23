"""bdbox action field type."""

from typing import Annotated

import tyro

from bdbox.actions.export import ExportAction
from bdbox.actions.run import RunAction
from bdbox.actions.view import ViewAction
from bdbox.actions.viewer import Start, Status, Stop

_Run = Annotated[
    RunAction,
    tyro.conf.subcommand("run", description="Run the model."),
]
_Export = Annotated[
    ExportAction,
    tyro.conf.subcommand(
        "export", description="Export geometry to a STEP or STL file."
    ),
]
_View = Annotated[
    ViewAction,
    tyro.conf.subcommand("view", description="View model geometry."),
]
ModelActionField = _Run | _Export | _View
ViewerActionField = Annotated[
    Start | Stop | Status,
    tyro.conf.subcommand("viewer", description="Viewer control"),
]
ActionField = ModelActionField | ViewerActionField
