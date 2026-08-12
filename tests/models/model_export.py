#!/usr/bin/env python3
"""Export test model (Model subclass)."""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field

from build123d import Box, BuildPart, BuildSketch, Compound, Rectangle, extrude

from bdbox import Float, Model, Preset, show


@dataclass
class SubOptions:
    x: float
    y: float
    z: float
    do_the_thing: bool = False


class ExportModel(Model):
    """A simple box model for export testing."""

    sub: SubOptions = field(default_factory=lambda: SubOptions(1, 2, 3))
    size = Float(10.0, min=1.0, max=100.0)
    presets = (Preset("mid", size=8.5),)
    use_show: str | None = None

    def build(self) -> Model.Geometry | None:
        """Build and return a box."""
        b1 = Box(self.size, self.size, self.size)
        with BuildPart() as p:
            with BuildSketch() as sk:
                Rectangle(self.size * 2, self.size * 2)
            extrude(amount=self.size, both=True)
            assert p.part
            p.part.label = "Box"
        b2 = p.part
        b3 = Box(self.size / 2, self.size / 2, self.size / 2)
        c1 = Compound(children=[b3, copy(b3), copy(b3)])
        if self.use_show:
            func = getattr(show, f"__{self.use_show}__", None)
            assert func, f"show.__{self.use_show}__ missing"
            show(sk, b2)
            func((b1, b2))
            func(b1)
            func(c1)
        return b1, b2, c1
