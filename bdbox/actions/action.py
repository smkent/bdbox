"""bdbox action base class."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar

import tyro  # noqa: TC002

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


@dataclass
class Action:
    """Base class for bdbox actions."""

    class Mode(Enum):
        EMBEDDED = auto()
        HARNESS = auto()

    mode: ClassVar[Action.Mode] = Mode.EMBEDDED
    watch: tyro.conf.Fixed[bool] = field(default=False, kw_only=True)

    @dataclass
    class HarnessResult:
        all_presets: bool = False
        preset_argv: Callable[[str | None], Sequence[str]] | None = None
        preset_action: Callable[[str | None], Action] | None = None

    BeforeHarnessResult = HarnessResult | None

    def __call__(self) -> None:
        """Execute this action with the given geometry."""
        raise NotImplementedError

    def before_harness(self) -> Action.BeforeHarnessResult:
        """Executed prior to running the harness."""

    def before_model(self) -> None:
        """Executed prior to running a model."""


@dataclass
class ModelAction(Action):
    def _ensure_runner(self) -> None:
        if self.mode != self.Mode.HARNESS:
            try:
                returncode = subprocess.run(  # noqa: S603, PLW1510
                    [sys.executable, "-m", "bdbox", *sys.argv]
                ).returncode
            except KeyboardInterrupt:
                sys.exit(130)
            except Exception:  # noqa: BLE001
                sys.exit(2)
            sys.exit(returncode)


@dataclass
class CommandAction(Action):
    def before_harness(self) -> Action.BeforeHarnessResult:
        self()

    def before_model(self) -> None:
        self()

    def __call__(self) -> None:
        sys.exit(0)
