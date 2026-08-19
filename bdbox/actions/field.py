"""bdbox action field type."""

from __future__ import annotations

import operator
from functools import reduce

from bdbox.actions.export import ExportAction
from bdbox.actions.run import RunAction
from bdbox.actions.version import VersionAction
from bdbox.actions.view import ViewAction

cli_actions = (RunAction, ExportAction, ViewAction, VersionAction)
ActionField = reduce(
    operator.or_, (action.cli.field for action in cli_actions)
)
