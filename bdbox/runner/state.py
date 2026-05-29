from __future__ import annotations

from dataclasses import dataclass, field

from bdbox.actions.state import ActionState
from bdbox.geometry.geometry import Geometry
from bdbox.model.state import ModelState


@dataclass
class RunState:
    geometry: Geometry = field(default_factory=Geometry)
    action_state: ActionState = field(default_factory=ActionState)
    model_state: ModelState = field(default_factory=ModelState)

    def reset(self) -> None:
        """Reset global bdbox state for runners or tests."""
        self.__init__()


run_state = RunState()
