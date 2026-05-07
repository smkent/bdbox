"""Exceptions for bdbox."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class Error(Exception):
    """Base class for all bdbox exceptions."""


class InternalError(Error):
    """Raised on unexpected internal state errors."""


@dataclass
class MultipleModelsError(Error):
    """Raise when multiple models are available but none were selected."""

    classes: Sequence[type] = ()

    @property
    def names(self) -> Sequence[str]:
        return sorted(c.__name__ for c in self.classes)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {', '.join(self.names)}"


class ParamsError(Error):
    """Raised for invalid parameters configuration."""


class ParamValidationError(Error, ValueError):
    """Raised when a parameter value fails validation."""


@dataclass
class RunError(Error):
    """Raised when a model run fails."""

    exception: Exception | SystemExit
