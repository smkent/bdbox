"""Parametric configuration and tooling for build123d models."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as import_version

from bdbox.errors import Error, ParamsError, ParamValidationError
from bdbox.geometry import show
from bdbox.model import Model
from bdbox.parameters.field_factories import Bool, Choice, Float, Int, Str
from bdbox.parameters.parameters import Params
from bdbox.parameters.preset import Preset

try:
    version = import_version(__name__)
except PackageNotFoundError:  # pragma: no cover
    version = "0.0.0"


__all__ = [
    "Bool",
    "Choice",
    "Error",
    "Float",
    "Int",
    "Model",
    "ParamValidationError",
    "Params",
    "ParamsError",
    "Preset",
    "Str",
    "show",
    "version",
]
