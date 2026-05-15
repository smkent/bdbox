from __future__ import annotations

import sys
from contextlib import ExitStack
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bdbox.actions.action import Action


@dataclass
class ActionState:
    """Holds the active action and manages its lifecycle."""

    def _run_action() -> Action:
        from bdbox.actions.run import RunAction  # noqa: PLC0415

        return RunAction()

    action: Action = field(default_factory=_run_action)
    acted: bool = False
    stack: ExitStack = field(default_factory=ExitStack, init=False, repr=False)

    def act_once(self) -> None:
        if self.acted:
            return
        self.acted = True
        self.action()

    def enter_on_model_render(self) -> None:
        self.stack.enter_context(self.action.on_model_render())

    def close_stack(self) -> bool | None:
        return self.stack.__exit__(*sys.exc_info())


action_state = ActionState()
