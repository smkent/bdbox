"""bdbox action base class."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar

import tyro  # noqa: TC002

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


@dataclass
class Action:
    """Base class for bdbox actions."""

    class Mode(Enum):
        EMBEDDED = auto()
        RUNNER = auto()

    mode: ClassVar[Action.Mode] = Mode.EMBEDDED
    watch: ClassVar[tyro.conf.Fixed[bool]] = False

    def __call__(self) -> None:
        """Execute this action with the given geometry."""
        raise NotImplementedError

    def before_harness_model(
        self, model: str | Path, argv: Sequence[str] = ()
    ) -> None:
        """Executed prior to model program start within ModelRunner."""

    def before_model(self) -> None:
        """Executed prior to model run."""
