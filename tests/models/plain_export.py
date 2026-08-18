#!/usr/bin/env python3
import atexit
from copy import copy

from build123d import Box, Compound


def _atexit_hook() -> None:
    print("Doing something at the end using atexit")  # noqa: T201


atexit.register(_atexit_hook)
_box = Box(2, 5, 10)
_c1 = Compound(children=[_box, copy(_box), copy(_box)])
result = (Box(20, 30, 40), Box(5, 10, 15), _c1)
