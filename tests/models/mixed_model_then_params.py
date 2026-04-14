#!/usr/bin/env python3
"""Mixed test with both Model and Params subclasses."""

from bdbox import Float, Model, Params


class MyModel(Model):
    width = Float(10.0)

    def build(self) -> None:
        pass


class P(Params):
    width = Float(10.0)
