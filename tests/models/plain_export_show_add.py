#!/usr/bin/env python3
from __future__ import annotations

from copy import copy

from build123d import Box, BuildPart, BuildSketch, Compound, Rectangle, extrude

from bdbox import show

size = 10


b1 = Box(size, size, size)
with BuildPart() as p:
    with BuildSketch() as sk:
        Rectangle(size * 2, size * 2)
    extrude(amount=size, both=True)
    assert p.part
    p.part.label = "Box"
b2 = p.part
b3 = Box(size / 2, size / 2, size / 2)
c1 = Compound(children=[b3, copy(b3), copy(b3)])


show(sk, b2)
show + (b1, b2)  # noqa: RUF005
show + b1
show((b1, b2))
show(c1)
