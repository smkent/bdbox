from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from types import ModuleType, TracebackType


@dataclass
class PatchModule:
    name: str
    original: ModuleType | None = field(default=None, init=False)
    replacement: ModuleType
    auto: bool = True
    started: bool = field(default=False, init=False)

    def __enter__(self) -> Self:
        if self.auto:
            self.start()
        return self

    def start(self) -> None:
        if not self.started:
            self.original = sys.modules.get(self.name)
            sys.modules[self.name] = self.replacement
        self.started = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        if not self.started:
            return
        if self.original:
            sys.modules[self.name] = self.original
        else:
            del sys.modules[self.name]
