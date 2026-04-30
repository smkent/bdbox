from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from bdbox.actions.run import RunAction
from bdbox.errors import MultipleModelsError, ParamsError

if TYPE_CHECKING:
    from collections.abc import Callable

    from bdbox.actions.action import Action


@dataclass
class RunState:
    filename: str | None = None
    module_name: str = "__main__"
    class_name: str | None = None
    model_subclasses: list[Any] = field(default_factory=list)
    action: Action = field(default_factory=RunAction)
    acted: bool = False

    class Mode(Enum):
        PARAMS_CLASS = auto()
        MODEL_CLASS = auto()

    mode: Mode | None = None

    def get_model(self) -> type[Any] | None:
        if not self.model_subclasses:
            return None
        if len(self.model_subclasses) == 1:
            subc = self.model_subclasses[0]
            if self.class_name and subc.__name__ != self.class_name:
                raise ParamsError(f"Model {self.class_name} not found")
            return subc
        if self.class_name:
            for subc in self.model_subclasses:
                if subc.__name__ == self.class_name:
                    return subc
            raise ParamsError(f"Model {self.class_name} not found")
        raise MultipleModelsError(self.model_subclasses)

    def ensure_mode(self, style: RunState.Mode, msg: str) -> None:
        if self.mode is not None and self.mode is not style:
            raise ParamsError(msg)
        self.mode = style

    def act_once(self, func: Callable[[], None]) -> None:
        if self.acted:
            return
        self.acted = True
        func()

    def is_class_in_main(self, cls: type) -> bool:
        return cls.__module__ in (
            "__main__",
            self.module_name,
        ) or cls.__module__.startswith(f"{self.module_name}.")

    def ensure_module_filename(self, cls: type) -> None:
        if (
            self.is_class_in_main(cls)
            and (mm := sys.modules.get(cls.__module__))
            and getattr(mm, "__file__", None)
            and self.filename
        ):
            mm.__file__ = self.filename


run_state = RunState()
