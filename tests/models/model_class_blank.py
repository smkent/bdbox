#!/usr/bin/env python3
"""Model subclass test model with no params for invocation tests."""

import os
from typing import Any

from bdbox import Model


class MyModel(Model):
    def build(self) -> Any:
        print("hm")  # noqa: T201
        return None


if os.environ.get("BDBOX_TEST_MODEL_MODE") == "run":
    MyModel.run()
