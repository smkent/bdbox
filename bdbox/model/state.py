from __future__ import annotations

import sys
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bdbox.errors import InternalError, MultipleModelsError, ParamsError
from bdbox.protocol import ModelNameInfo
from bdbox.serializer import serializer
from bdbox.timer import Timer

from .info import ModelInfo

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .parameters import Params


@dataclass
class ModelState:
    model: ModelInfo = field(default_factory=ModelInfo)
    module_dict: dict[str, Any] = field(default_factory=dict, repr=False)
    model_subclasses: list[Any] = field(default_factory=list)
    model_cli: Params | None = None
    timer: Timer | None = field(default=None)

    param_overrides: dict[str, Any] = field(default_factory=dict)
    resolved_values: dict[str, Any] = field(default_factory=dict)
    cached_schema: dict[str, Any] = field(
        default_factory=dict, repr=False, init=False
    )

    def apply_overrides(self, target: Params) -> None:
        hints = serializer.get_type_hints(type(target))

        for name, raw_value in self.param_overrides.items():
            if not hasattr(target, name):
                continue
            hint = hints.get(name)
            if hint is None:
                current = getattr(target, name)
                hint = type(current) if current is not None else None
            setattr(target, name, serializer.structure(raw_value, hint))

    def get_model(self) -> type[Params] | None:
        if not self.model_subclasses:
            return None
        if len(self.model_subclasses) == 1:
            subc = self.model_subclasses[0]
            if (
                self.model.class_name
                and subc.__name__ != self.model.class_name
            ):
                raise ParamsError(f"Model {self.model.class_name} not found")
            return subc
        if self.model.class_name:
            for subc in self.model_subclasses:
                if subc.__name__ == self.model.class_name:
                    return subc
            raise ParamsError(f"Model {self.model.class_name} not found")
        raise MultipleModelsError(self.model_subclasses)

    def model_name_info(self) -> ModelNameInfo:
        return ModelNameInfo(
            file=(
                Path(self.model.filename).stem
                if self.model.filename and not self.model.module_name
                else None
            ),
            module=self.model.module_name,
            cls=self.model.class_name,
        )

    def model_name(self) -> str:
        if (
            self.model.mode == self.model.Mode.PARAMS_CLASS
            and self.model.filename
        ):
            return Path(self.model.filename).stem
        with suppress(InternalError):
            if model_class := self.get_model():
                return model_class.__name__
        if self.model.filename:
            return Path(self.model.filename).stem
        raise InternalError("Unable to determine model name")

    def ensure_module_filename(self, cls: type) -> None:
        if (
            self.model.is_class_in_main(cls)
            and (mm := sys.modules.get(cls.__module__))
            and getattr(mm, "__file__", None)
            and self.model.filename
        ):
            mm.__file__ = self.model.filename

    @property
    def schema(self) -> dict[str, Any]:
        if self.cached_schema:
            return self.cached_schema
        if model_class := self.get_model():
            return serializer.json_schema(model_class)
        return {}

    @property
    def model_running(self) -> bool:
        return self.timer is not None

    @contextmanager
    def set_running(self) -> Iterator[Timer]:
        if not self.cached_schema:
            self.cached_schema = self.schema
        was_timer = self.timer
        self.timer = Timer()
        try:
            yield self.timer
        finally:
            self.timer = was_timer


model_state = ModelState()
