"""Runtime geometry collection utilities."""

from __future__ import annotations

import sys
from enum import Enum, auto
from typing import Any

from bdbox.errors import ParamsError


class _Mode(Enum):
    PARAMS_CLASS = auto()
    MODEL_CLASS = auto()


class GeometryMode:
    """Guards against mixing parameter modes in the same model."""

    _mode: _Mode | None = None

    @classmethod
    def ensure_params_class_mode(cls) -> None:
        """Ensure ``Params`` subclass is the only active mode.

        Raises:
            ParamsError: If a ``Model`` subclass is already defined.
        """
        cls._check(
            _Mode.PARAMS_CLASS,
            "Cannot use Params subclass with an existing Model subclass",
        )

    @classmethod
    def ensure_model_class_mode(cls, name: str) -> None:
        """Ensure ``Model`` subclass is the only active mode.

        Raises:
            ParamsError: If a ``Params`` subclass is already defined.
        """
        cls._check(
            _Mode.MODEL_CLASS,
            f"Cannot define Model subclass {name!r}"
            " with an existing Params subclass",
        )

    @classmethod
    def _check(cls, style: _Mode, msg: str) -> None:
        if cls._mode is not None and cls._mode is not style:
            raise ParamsError(msg)
        cls._mode = style


# Geometry collected via show() calls during execution.
_geometry: list[Any] = []


def show(*args: Any) -> None:
    """Provide built model geometry for display or use.

    Info:
        With a [``Params``][bdbox.parameters.parameters.Params] subclass,
        call `show` with your built model geometry. Multiple `show` calls
        accumulate geometry in order.

        With a [``Model``][bdbox.model.Model] subclass, return geometry
        from the [``build``][bdbox.model.Model.build] method instead of calling
        `show`.

    Note:
        If ``show()`` is never called, bdbox falls back to scanning the
        script's globals for [``build123d.Shape``][topology.Shape] instances,
        but calling ``show()`` manually is recommended.
    """
    _geometry.extend(args)


def resolve_geometry() -> list[Any]:
    """Retrieve geometry for processing.

    Uses geometry collected by ``show()`` if called. Otherwise falls back to
    scanning ``__main__`` globals for build123d ``Shape`` instances.
    """
    if _geometry:
        return list(_geometry)
    return _scan_main_globals()


def _scan_main_globals() -> list[Any]:
    """Scan ``__main__`` globals for build123d ``Shape`` instances."""
    if "build123d" not in sys.modules:
        return []
    from build123d import Shape  # noqa: PLC0415

    main = sys.modules.get("__main__")
    if main is None:
        return []

    return [
        v
        for k, v in vars(main).items()
        if not k.startswith("_") and isinstance(v, Shape)
    ]
