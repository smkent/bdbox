#!/usr/bin/env python3
"""Params subclass test model."""

import os

from bdbox import Bool, Choice, Float, Int, Params, Preset, Str, show

if os.environ.get("BDBOX_TEST_MODEL_MODE", "") != "show_noparams":

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
else:
    print("params() not called")  # noqa: T201

if os.environ.get("BDBOX_TEST_MODEL_MODE") in {"show", "show_noparams"}:
    show()
