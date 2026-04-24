#!/usr/bin/env python3
"""Params subclass test model."""

import os
from dataclasses import dataclass, field

from bdbox import Bool, Choice, Float, Int, Params, Preset, Str, show


@dataclass
class SubSub:
    x: int = Int(5, min=0, max=10)


@dataclass
class SubOptions:
    subsub: SubSub
    a: float
    b: float = 5.0
    c: float = Float(25.0, min=0, max=2000.0, description="C!")
    do_the_thing: bool = False  # Zhu Li, do the thing!
    do_another_thing: bool = Bool(default=False, description="Another thing?")


if os.environ.get("BDBOX_TEST_MODEL_MODE", "") != "show_noparams":

    class P(Params):
        sub: SubOptions = field()
        aa = 5
        sub2: SubOptions = field(
            default_factory=lambda: SubOptions(SubSub(), 1, 2, 3)
        )
        width = Float(10.0, min=1.0, max=100.0)
        height = Int(5, min=1, max=50)
        enabled = Bool(default=False, description="enable the thing")
        text = Str("nope")
        thing = Choice("first", ["first", "second", "third"])
        count: int = 1
        presets = (
            Preset("default"),
            Preset("large", width=50.0, height=25),
            Preset("small", width=2, height=2, thing="third"),
        )

    print(  # noqa: T201
        f"{P.width}x{P.height},en={P.enabled},thing={P.thing},text={P.text}"
    )
else:
    print("params() not called")  # noqa: T201

if os.environ.get("BDBOX_TEST_MODEL_MODE") in {"show", "show_noparams"}:
    show()
