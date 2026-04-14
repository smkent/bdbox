#!/usr/bin/env python3
"""Multiple Model subclasses for testing."""

import os
from typing import Any

from bdbox import Float, Int, Model


class FirstModel(Model):
    width = Float(10.0, min=1.0, max=100.0)

    def build(self) -> Any:
        print(self.__class__.__name__, self.width)  # noqa: T201


class SecondModel(Model):
    height = Int(10, min=1, max=100)

    def build(self) -> Any:
        print(self.__class__.__name__, self.height)  # noqa: T201


if os.environ.get("BDBOX_TEST_MODEL_MODE") == "run":
    FirstModel.run()
