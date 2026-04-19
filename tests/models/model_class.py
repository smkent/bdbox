#!/usr/bin/env python3
"""Model subclass test model."""

import os
from dataclasses import dataclass, field
from typing import Any

from bdbox import Bool, Choice, Float, Int, Model, Preset, Str


@dataclass
class SubOptions:
    a: float
    b: float
    c: float
    do_the_thing: bool = False


class MyModel(Model):
    sub: SubOptions = field(default_factory=lambda: SubOptions(1, 2, 3))
    width = Float(10.0, min=1.0, max=100.0)
    height = Int(5, min=1, max=50)
    enabled = Bool(default=False, description="enable the thing")
    text = Str("nope")
    thing = Choice("first", ["first", "second", "third"])
    count: int = 1
    presets = (
        Preset("default"),
        Preset("large", width=50.0),
        Preset("small", width=2, height=2, thing="third"),
        Preset("plain", count=2),
    )

    def build(self) -> Any:
        print(  # noqa: T201
            f"{self.width}x{self.height}"
            f",en={self.enabled}"
            f",thing={self.thing}"
            f",text={self.text}"
        )
        return None


if os.environ.get("BDBOX_TEST_MODEL_MODE") == "run":
    MyModel.run()
