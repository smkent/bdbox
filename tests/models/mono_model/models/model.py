from __future__ import annotations

from enum import Enum, auto
from typing import Any

from tests.models.utils import build123d

assert build123d

from build123d import Box  # noqa: E402

from bdbox import Float, Int, Model  # noqa: E402
from tests.models.mono_model.misc.constants import Defaults  # noqa: E402


class Material(Enum):
    TRANSPARENT_ALUMINUM = auto()
    NEUTRONIUM = auto()
    DURANIUM = auto()


class MyModel(Model):
    a: float = Defaults.A
    b: int = Defaults.B
    c = Int(Defaults.C, min=1, max=10)
    d = Float(Defaults.D, min=1.0, max=10.0)
    material: Material = Material.TRANSPARENT_ALUMINUM

    def build(self) -> Any:
        b1 = Box(self.a, self.b, self.c)
        b2 = Box(self.b, self.c, self.d)
        print("b1", b1)  # noqa: T201
        print("b2", b2)  # noqa: T201
        return b1, b2
