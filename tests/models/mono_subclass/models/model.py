from __future__ import annotations

from typing import Any

from tests.models.utils import build123d

assert build123d

from build123d import Mode  # noqa: E402

from bdbox import Float, Model  # noqa: E402
from tests.models.mono_subclass.shapes.pattern import (  # noqa: E402
    CustomCircle,
)


class MyModel(Model):
    radius = Float(5.0, min=1.0, max=20.0)

    def build(self) -> Any:
        return CustomCircle(self.radius, mode=Mode.ADD)
