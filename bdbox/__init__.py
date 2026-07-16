"""build123d development with live preview and interactive parameters."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as import_version

from bdbox.errors import (
    Error,
    InternalError,
    MultipleModelsError,
    ParamsError,
    ParamValidationError,
    RunError,
)
from bdbox.geometry.show import show
from bdbox.model.field_factories import Bool, Choice, Float, Inches, Int, Str
from bdbox.model.model import Model
from bdbox.model.parameters import Params
from bdbox.model.preset import Preset

try:
    version = import_version(__name__)
except PackageNotFoundError:  # pragma: no cover
    version = "0.0.0"


__all__ = [
    "Bool",
    "Choice",
    "Error",
    "Float",
    "Inches",
    "Int",
    "InternalError",
    "Model",
    "MultipleModelsError",
    "ParamValidationError",
    "Params",
    "ParamsError",
    "Preset",
    "RunError",
    "Str",
    "show",
    "version",
]
