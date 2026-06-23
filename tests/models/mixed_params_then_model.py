#!/usr/bin/env python3
"""Mixed test with both Params and Model subclasses."""

from bdbox import Float, Model, Params


class P(Params):
    width = Float(10.0)


class MyModel(Model):
    width = Float(10.0)

    def build(self) -> None:
        pass
