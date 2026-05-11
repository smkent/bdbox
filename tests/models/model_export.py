#!/usr/bin/env python3
"""Export test model (Model subclass)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from build123d import Box, Compound

from bdbox import Float, Model, Preset

if TYPE_CHECKING:
    from collections.abc import Sequence


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

    def build(self) -> Compound | Sequence[Compound]:
        """Build and return a box."""
        return (
            Box(self.size, self.size, self.size),
            Box(self.size * 2, self.size * 2, self.size * 2),
        )
