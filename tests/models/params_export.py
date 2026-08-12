#!/usr/bin/env python3
"""Export test model (Params style)."""

from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field

from build123d import Box, BuildPart, BuildSketch, Compound, Rectangle, extrude

from bdbox import Float, Params, Preset, show


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
    use_show: str | None = None


_b1 = Box(P.size, P.size, P.size)
with BuildPart() as _p:
    with BuildSketch() as _sk:
        Rectangle(P.size * 2, P.size * 2)
    extrude(amount=P.size, both=True)
    assert _p.part
    _p.part.label = "Box"
_b2 = _p.part
_b3 = Box(P.size / 2, P.size / 2, P.size / 2)
_c1 = Compound(children=[_b3, copy(_b3), copy(_b3)])


if P.use_show:
    func = getattr(show, f"__{P.use_show}__", None)
    assert func, f"show.__{P.use_show}__ missing"
    show(_sk, _b2)
    func((_b1, _b2))
    func(_b1)
    func(_c1)
    show((_b1, _b2))
    show(_c1)
else:
    result = (_b1, _b2, _c1)
