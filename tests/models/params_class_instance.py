#!/usr/bin/env python3
"""Params-style bdbox model fixture for invocation tests."""

from bdbox import Bool, Choice, Float, Int, Params, Preset, Str


class P(Params):
    width = Float(10.0, min=1.0, max=100.0)
    height = Int(5, min=1, max=50)
    enabled = Bool(default=False, description="enable the thing")
    text = Str("nope")
    thing = Choice("first", ["first", "second", "third"])
    presets = (
        Preset("default"),
        Preset("large", width=50.0),
        Preset("small", width=2, height=2, thing="third"),
    )


p = P(preset="large")

print(  # noqa: T201
    f"{p.width}x{p.height},en={p.enabled},thing={p.thing},text={p.text}"
)
