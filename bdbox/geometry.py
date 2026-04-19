"""Runtime geometry collection utilities."""

from __future__ import annotations

import sys
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, ClassVar

from bdbox.errors import ParamsError

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class Geometry:
    """Guards against mixing parameter modes in the same model."""

    # Geometry collected via show() calls during execution.
    geometry: ClassVar[list[Any]] = []

    class Mode(Enum):
        PARAMS_CLASS = auto()
        MODEL_CLASS = auto()

    mode: ClassVar[Mode | None] = None

    @classmethod
    def reset(cls) -> None:
        """Clear any active mode information for runners or tests."""
        cls.clear_geometry()
        cls.mode = None

    @classmethod
    def ensure_params_class_mode(cls) -> None:
        """Ensure ``Params`` subclass is the only active mode.

        Raises:
            ParamsError: If a ``Model`` subclass is already defined.
        """
        cls.ensure_mode(
            cls.Mode.PARAMS_CLASS,
            "Cannot use Params subclass with an existing Model subclass",
        )

    @classmethod
    def ensure_model_class_mode(cls, name: str) -> None:
        """Ensure ``Model`` subclass is the only active mode.

        Raises:
            ParamsError: If a ``Params`` subclass is already defined.
        """
        cls.ensure_mode(
            cls.Mode.MODEL_CLASS,
            f"Cannot define Model subclass {name!r}"
            " with an existing Params subclass",
        )

    @classmethod
    def ensure_mode(cls, style: Geometry.Mode, msg: str) -> None:
        if cls.mode is not None and cls.mode is not style:
            raise ParamsError(msg)
        cls.mode = style

    @classmethod
    def accumulate_geometry(cls, shapes: Sequence[Any]) -> None:
        cls.geometry.extend(cls.filter_geometry(shapes))

    @classmethod
    def clear_geometry(cls) -> None:
        cls.geometry = []

    @classmethod
    def filter_geometry(cls, shapes: Sequence[Any]) -> list[Any]:
        if "build123d" not in sys.modules:
            return []
        from build123d import Shape  # noqa: PLC0415

        with suppress(TypeError):
            return [s for s in shapes if isinstance(s, Shape)]
        return []

    @classmethod
    def resolve_geometry(cls) -> list[Any]:
        if not Geometry.geometry:
            if "build123d" not in sys.modules:
                return []

            if (mod := sys.modules.get("__main__")) and (
                shapes := cls.filter_geometry(
                    [v for k, v in vars(mod).items() if not k.startswith("_")]
                )
            ):
                Geometry.accumulate_geometry(shapes)
        return Geometry.geometry


def reset_geometry() -> None:
    """Clear collected geometry for runners or tests."""
    Geometry.reset()


def resolve_geometry() -> list[Any]:
    """Retrieve geometry for processing.

    Uses geometry collected by ``show()`` if called. Otherwise falls back to
    scanning ``__main__`` globals for build123d ``Shape`` instances.
    """
    return Geometry.resolve_geometry()


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
    Geometry.accumulate_geometry(args)
