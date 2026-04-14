#!/usr/bin/env python3
"""Script-style bdbox model fixture for invocation tests."""

from bdbox import Bool, Choice, Float, Int, Params, Preset, Str


class P(Params):
    width = Float(10.0, min=1.0, max=100.0)
    height = Int(5, min=1, max=50)
    enabled = Bool(default=False, description="enable the thing")
    text = Str("nope")
    thing = Choice("first", ["first", "second", "third"])
    presets = (
        Preset("default"),
        Preset("large", width=50.0, height=25),
        Preset("small", width=2, height=2, thing="third"),
    )


print(  # noqa: T201
    f"{P.width}x{P.height},en={P.enabled},thing={P.thing},text={P.text}"
)


class AnotherP(Params):
    bottom = Bool(default=False)
    top = Float(20.0, min=0.0, max=50.0)


print(f"p2:{AnotherP.bottom},{AnotherP.top}")  # noqa: T201
