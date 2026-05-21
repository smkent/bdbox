from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from bdbox.errors import ParamsError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ModelInfo:
    filename: str | None = None
    module_name: str | None = None
    class_name: str | None = field(default=None, init=False)
    path: Path | None = field(default=None, init=False)

    class Mode(Enum):
        PARAMS_CLASS = auto()
        MODEL_CLASS = auto()

    mode: Mode | None = None

    def ensure_mode(self, style: ModelInfo.Mode, msg: str) -> None:
        if self.mode is not None and self.mode is not style:
            raise ParamsError(msg)
        self.mode = style

    def is_class_in_main(self, cls: type) -> bool:
        return cls.__module__ in (
            "__main__",
            self.module_name or "__main__",
        ) or cls.__module__.startswith(f"{self.module_name}.")
