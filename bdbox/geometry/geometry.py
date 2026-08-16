"""Runtime geometry collection utilities."""

from __future__ import annotations

import copy
import sys
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bdbox.console import log

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from build123d import (
        Builder,
        Compound,
        Joint,
        Location,
        LocationList,
        Plane,
        Shape,
    )

    BaseGeometry = (
        Builder | Compound | Joint | Location | LocationList | Plane | Shape
    )
    """Supported build123d base types for [``show``][bdbox.geometry.show.show].

    For full geometry types accepted by [``show``][bdbox.geometry.show.show],
    see [``Geometry``][bdbox.geometry.geometry.Geometry].

    Info:
        Only available for static type checking.
    """

    Geometry = (
        BaseGeometry
        | Sequence[BaseGeometry | None]
        | Mapping[str, BaseGeometry | None]
    )
    """Geometry types accepted by [``show``][bdbox.geometry.show.show].

    See [``BaseGeometry``][bdbox.geometry.geometry.BaseGeometry] for
    supported build123d base types.

    Info:
        Only available for static type checking.
    """

    ResolvedGeometry = Compound | Shape


@dataclass
class GeometryCollector:
    # Geometry collected via show() calls during execution.
    geometry: list[ResolvedGeometry] = field(default_factory=list)

    @property
    def max_diagonal(self) -> float:
        diagonal = 0
        for g in self.geometry:
            if not (bounding_box := getattr(g, "bounding_box", None)):
                continue
            with suppress(AttributeError, ValueError):
                diagonal = max(diagonal, bounding_box(optimal=False).diagonal)
        return diagonal

    def accumulate_geometry(self, *shapes: Geometry | None) -> None:
        self.geometry.extend(
            [shape for s in shapes if (shape := self.filter_geometry(s))]
        )

    def filter_geometry(
        self, data: Any, label: str = ""
    ) -> ResolvedGeometry | None:
        if "build123d" not in sys.modules:
            return None
        from build123d import (  # noqa: PLC0415
            Builder,
            Compound,
            Joint,
            Location,
            LocationList,
            Plane,
            Shape,
        )

        geometry = None
        with suppress(TypeError):
            if isinstance(data, Shape):
                return data
            if isinstance(data, Builder):
                obj = getattr(data, data._obj_name, None)  # noqa: SLF001
                return obj if isinstance(obj, Shape) else None
            if isinstance(data, Joint):
                label = label or f"{data.label} {type(data).__name__}"
                try:
                    symbol = copy.copy(data.symbol)
                    symbol.label = label
                except AttributeError:
                    return self.filter_geometry(data.location, label)
                else:
                    return symbol
            if isinstance(data, Plane):
                return self.filter_geometry(
                    data.location, label=label or f"{type(data).__name__}"
                )
            if isinstance(data, LocationList):
                if len(data.locations) != 1:
                    return self.filter_geometry(
                        data.locations, label=label or f"{type(data).__name__}"
                    )
                data = data.locations[0]
            if isinstance(data, Location):
                axes_scale = (self.max_diagonal / 12) or 10
                obj = Compound.make_triad(axes_scale=axes_scale).move(data)
                obj.label = label or f"{type(data).__name__}"
                return obj
            if isinstance(data, (list, tuple)):
                geometry = [c for s in data if (c := self.filter_geometry(s))]
            elif isinstance(data, dict):
                geometry = [
                    c
                    for k, v in data.items()
                    if (c := self.filter_geometry(v, str(k)))
                ]
        if not geometry:
            return None
        geometry = list({id(g): g for g in geometry}.values())
        if len(geometry) == 1:
            return geometry[0]
        return Compound(label=label, children=geometry)

    def resolve(self) -> ResolvedGeometry | None:
        if "build123d" not in sys.modules:
            return None

        if not self.geometry and (mod := sys.modules.get("__main__")):
            found_geometry = [
                geo
                for var_name, value in vars(mod).items()
                if not var_name.startswith("_")
                and (geo := self.filter_geometry(value, str(var_name)))
            ]
            self.accumulate_geometry(*found_geometry)
        label = "bdbox collected geometry"
        geometry = self.filter_geometry(self.geometry, label=label)
        if not geometry:
            return None
        try:
            log.debug(geometry.show_topology(limit_class="Solid"))
        except Exception:  # noqa: BLE001
            log.exception("Error showing geometry topology")
        return geometry
