"""Runtime geometry collection utilities."""

from __future__ import annotations

import sys
from contextlib import suppress
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bdbox.console import log

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from build123d import Compound, Shape


@dataclass
class Geometry:
    # Geometry collected via show() calls during execution.
    geometry: list[Compound | Shape] = field(default_factory=list)

    def accumulate_geometry(
        self,
        *shapes: Compound
        | Shape
        | Sequence[Compound | Shape]
        | Mapping[str, Compound | Shape],
    ) -> None:
        self.geometry.extend(
            [shape for s in shapes if (shape := self.filter_geometry(s))]
        )

    def filter_geometry(
        self, data: Any, label: str = ""
    ) -> Compound | Shape | None:
        if "build123d" not in sys.modules:
            return None
        from build123d import Compound, Shape  # noqa: PLC0415

        geometry = None
        with suppress(TypeError):
            if isinstance(data, Shape):
                return data
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
        if len(geometry) == 1:
            return geometry[0]
        return Compound(label=label, children=geometry)

    def resolve(self) -> Compound | Shape | None:
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
