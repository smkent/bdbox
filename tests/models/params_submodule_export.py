#!/usr/bin/env python3
"""Export test model using a build123d sub-module import (Params style)."""

from __future__ import annotations

from build123d import Box
from build123d.topology import Shape

from bdbox import Float, Params, Preset


class P(Params):
    size = Float(10.0, min=1.0, max=100.0)
    presets = (Preset("small", size=5.0),)


box = Box(P.size, P.size, P.size)
if not isinstance(box, Shape):
    raise TypeError(f"Expected Shape instance, got {type(box)}")
