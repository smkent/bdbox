"""Runtime geometry collection utilities."""

from __future__ import annotations

import sys
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, ClassVar

from bdbox.errors import ParamsError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from build123d import Compound, Shape


@dataclass
class Geometry:
    # Geometry collected via show() calls during execution.
    geometry: ClassVar[list[Compound | Shape]] = []

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
    def accumulate_geometry(
        cls,
        *shapes: Compound
        | Shape
        | Sequence[Compound | Shape]
        | Mapping[str, Compound | Shape],
    ) -> None:
        cls.geometry.extend(
            [shape for s in shapes if (shape := cls.filter_geometry(s))]
        )

    @classmethod
    def clear_geometry(cls) -> None:
        cls.geometry = []

    @classmethod
    def filter_geometry(
        cls, data: Any, label: str = ""
    ) -> Compound | Shape | None:
        if "build123d" not in sys.modules:
            return None
        from build123d import Compound, Shape  # noqa: PLC0415

        geometry = None
        with suppress(TypeError):
            if isinstance(data, Shape):
                return data
            if isinstance(data, (list, tuple)):
                geometry = [c for s in data if (c := cls.filter_geometry(s))]
            elif isinstance(data, dict):
                geometry = [
                    c
                    for k, v in data.items()
                    if (c := cls.filter_geometry(v, str(k)))
                ]
        if not geometry:
            return None
        if len(geometry) == 1:
            return geometry[0]
        return Compound(label=label, children=geometry)

    @classmethod
    def resolve_geometry(cls) -> Compound | Shape | None:
        if "build123d" not in sys.modules:
            return None

        if not Geometry.geometry and (mod := sys.modules.get("__main__")):
            found_geometry = [
                geo
                for var_name, value in vars(mod).items()
                if not var_name.startswith("_")
                and (geo := cls.filter_geometry(value, str(var_name)))
            ]
            Geometry.accumulate_geometry(*found_geometry)
        label = "bdbox collected geometry"
        geometry = cls.filter_geometry(Geometry.geometry, label=label)
        if not geometry:
            return None
        print(geometry.show_topology(limit_class="Solid"))  # noqa: T201
        return geometry


def reset_geometry() -> None:
    """Clear collected geometry for runners or tests."""
    Geometry.reset()


def resolve_geometry() -> Compound | Shape | None:
    """Retrieve geometry for processing.

    Uses geometry collected by ``show()`` if called. Otherwise falls back to
    scanning ``__main__`` globals for build123d ``Shape`` instances.
    """
    return Geometry.resolve_geometry()


def show(
    *geometry: Compound
    | Shape
    | Sequence[Compound | Shape]
    | Mapping[str, Compound | Shape],
) -> None:
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
    Geometry.accumulate_geometry(*geometry)
