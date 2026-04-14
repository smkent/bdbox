#!/usr/bin/env python3
"""Model subclass test with further derived test subclass."""

import os
from typing import Any

from bdbox import Float, Int, Model


class ParentModel(Model):
    width = Float(10.0, min=1.0, max=100.0)

    def build(self) -> Any:
        print(self.__class__.__name__, self.width)  # noqa: T201


class ChildModel(ParentModel):
    height = Int(10, min=1, max=100)

    def build(self) -> Any:
        print(self.__class__.__name__, self.width, self.height)  # noqa: T201


if os.environ.get("BDBOX_TEST_MODEL_MODE") == "run":
    ChildModel.run()
