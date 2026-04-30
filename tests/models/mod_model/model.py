from dataclasses import dataclass
from typing import Any

from bdbox import Float, Int, Model


@dataclass
class Box:
    x: float
    y: float
    z: float


class SomeModel(Model):
    a: float = 2.5
    b: int = 3
    c = Int(5, min=1, max=10)
    d = Float(5.0, min=1.0, max=10.0)

    def build(self) -> tuple[Any, ...]:
        b1 = Box(self.a, self.b, self.c)
        b2 = Box(self.b, self.c, self.d)
        print("b1", b1)  # noqa: T201
        print("b2", b2)  # noqa: T201
        return b1, b2
