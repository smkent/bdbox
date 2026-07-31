#!/usr/bin/env python3
from __future__ import annotations

from build123d import Box, BuildPart, BuildSketch, Rectangle, extrude

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


show(sk, b2)
show // (b1, b2)
show // b1
show((b1, b2))
