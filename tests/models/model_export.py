#!/usr/bin/env python3
"""Export test model (Model subclass)."""

from dataclasses import dataclass, field

from build123d import Box

from bdbox import Float, Model, Preset


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

    def build(self) -> Box:
        """Build and return a box."""
        return Box(self.size, self.size, self.size)
