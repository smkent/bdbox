#!/usr/bin/env python3
"""Params subclass test model with no params for invocation tests."""

from bdbox import Params


class P(Params):
    pass


print("Blank model!")  # noqa: T201
