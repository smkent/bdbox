from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from bdbox.geometry import reset_geometry
from bdbox.parameters.state import run_state

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import ModuleType, TracebackType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


def reset_bdbox() -> None:
    """Reset all bdbox module-level state for runners or tests."""
    reset_geometry()
    run_state.__init__()


class Build123dStub(MagicMock):
    MC = 0.001
    MM = 1
    CM = 10 * MM
    M = 1000 * MM
    IN = 25.4 * MM
    FT = 12 * IN
    THOU = IN / 1000
    G = 1
    KG = 1000 * G
    LB = 453.59237 * G


@contextmanager
def exit_mock() -> Iterator[None]:
    @dataclass
    class ExitError(Exception):
        code: int | str

    def stub(code: str | int) -> None:
        raise ExitError(code)

    with patch.object(sys, "exit", stub), patch.object(os, "_exit", stub):
        try:
            yield
        except ExitError as e:
            raise SystemExit(e.code) from e


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
