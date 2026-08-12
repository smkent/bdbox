#!/usr/bin/env python3
from copy import copy

from build123d import Box, Compound

_box = Box(2, 5, 10)
_c1 = Compound(children=[_box, copy(_box), copy(_box)])
result = (Box(20, 30, 40), Box(5, 10, 15), _c1)
