from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from bdbox.actions.state import ActionState
from bdbox.geometry.geometry import GeometryCollector
from bdbox.model.state import ModelState


@dataclass
class RunState:
    geometry: GeometryCollector = field(default_factory=GeometryCollector)
    action_state: ActionState = field(default_factory=ActionState)
    model_state: ModelState = field(default_factory=ModelState)

    class Mode(Enum):
        EMBEDDED = auto()
        HARNESS = auto()

    mode: Mode = field(default=Mode.EMBEDDED)

    def reset(self) -> None:
        """Reset global bdbox state for runners or tests."""
        self.__init__()


run_state = RunState()
