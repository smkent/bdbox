from __future__ import annotations

from dataclasses import dataclass, field

from bdbox.actions.state import ActionState
from bdbox.geometry import reset_geometry
from bdbox.model.state import ModelState


@dataclass
class RunState:
    action_state: ActionState = field(default_factory=ActionState)
    model_state: ModelState = field(default_factory=ModelState)

    def reset(self) -> None:
        """Reset global bdbox state for runners or tests."""
        self.__init__()
        reset_geometry()
        return


run_state = RunState()
