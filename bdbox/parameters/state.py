from __future__ import annotations

import sys
from contextlib import ExitStack, suppress
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bdbox.actions.run import RunAction
from bdbox.errors import InternalError, MultipleModelsError, ParamsError

from .serializer import Serializer

if TYPE_CHECKING:
    from bdbox.actions.action import Action

    from .parameters import Params


@dataclass
class RunState:
    filename: str | None = None
    module_name: str = "__main__"
    class_name: str | None = None
    module_dict: dict[str, Any] = field(
        default_factory=dict, init=False, repr=False
    )
    model_subclasses: list[Any] = field(default_factory=list)
    model_cli: Params | None = None
    action: Action = field(default_factory=RunAction)
    acted: bool = False
    stack: ExitStack = field(default_factory=ExitStack, init=False)
    serializer: Serializer = field(default_factory=Serializer, init=False)

    class Mode(Enum):
        PARAMS_CLASS = auto()
        MODEL_CLASS = auto()

    mode: Mode | None = None
    param_overrides: dict[str, Any] = field(default_factory=dict)
    resolved_values: dict[str, Any] = field(default_factory=dict)

    def apply_overrides(self, target: Params) -> None:
        hints = self.serializer.get_type_hints(type(target))

        for name, raw_value in self.param_overrides.items():
            if not hasattr(target, name):
                continue
            hint = hints.get(name)
            if hint is None:
                current = getattr(target, name)
                hint = type(current) if current is not None else None
            setattr(target, name, self.serializer.structure(raw_value, hint))

    def enter_on_model_render(self) -> None:
        if self.action:
            self.stack.enter_context(self.action.on_model_render())

    def close_stack(self) -> bool | None:
        return self.stack.__exit__(*sys.exc_info())

    def get_model(self) -> type[Params] | None:
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

    def model_name_info(self) -> dict[str, str | None]:
        module = self.module_name if self.module_name != "__main__" else None
        file = (
            Path(self.filename).stem if self.filename and not module else None
        )
        return {"file": file, "module": module, "cls": self.class_name}

    def model_name(self) -> str:
        if self.mode == self.Mode.PARAMS_CLASS and self.filename:
            return Path(self.filename).stem
        with suppress(InternalError):
            if model_class := self.get_model():
                return model_class.__name__
        if self.filename:
            return Path(self.filename).stem
        raise InternalError("Unable to determine model name")

    def ensure_mode(self, style: RunState.Mode, msg: str) -> None:
        if self.mode is not None and self.mode is not style:
            raise ParamsError(msg)
        self.mode = style

    def act_once(self) -> None:
        if self.acted:
            return
        self.acted = True
        self.action()

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
