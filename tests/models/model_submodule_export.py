#!/usr/bin/env python3
"""Export test model using a build123d sub-module import (Model subclass)."""

from __future__ import annotations

from build123d import Box
from build123d.topology import Shape

from bdbox import Float, Model, Preset


class SubmoduleModel(Model):
    size = Float(10.0, min=1.0, max=100.0)
    presets = (Preset("small", size=5.0),)

    def build(self) -> Shape:
        box = Box(self.size, self.size, self.size)
        if not isinstance(box, Shape):
            raise TypeError(f"Expected Shape instance, got {type(box)}")
        return box
