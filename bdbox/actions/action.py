"""bdbox action base class."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

import tyro  # noqa: TC002


@dataclass
class Action:
    """Base class for bdbox actions."""

    class Mode(Enum):
        EMBEDDED = auto()
        HARNESS = auto()

    mode: ClassVar[Action.Mode] = Mode.EMBEDDED
    watch: ClassVar[tyro.conf.Fixed[bool]] = False

    def __call__(self) -> None:
        """Execute this action with the given geometry."""
        raise NotImplementedError

    def before_model(self) -> None:
        """Executed prior to running a model."""


@dataclass
class ModelAction(Action):
    pass
