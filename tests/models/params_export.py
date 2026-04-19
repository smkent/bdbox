#!/usr/bin/env python3
"""Export test model (Params style)."""

from dataclasses import dataclass, field

from build123d import Box

from bdbox import Float, Params, Preset


@dataclass
class SubOptions:
    x: float
    y: float
    z: float
    do_the_thing: bool = False


class P(Params):
    """Parameters for export test."""

    sub: SubOptions = field(default_factory=lambda: SubOptions(1, 2, 3))
    size = Float(10.0, min=1.0, max=100.0)
    presets = (Preset("mid", size=8.5),)


box = Box(P.size, P.size, P.size)
