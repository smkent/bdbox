"""bdbox action field type."""

from typing import Annotated

import tyro

from bdbox.actions.export import ExportAction
from bdbox.actions.run import RunAction

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
ActionField = _Run | _Export
