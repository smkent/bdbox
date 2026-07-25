from __future__ import annotations

from dataclasses import dataclass

from bdbox import Float, Int, Model, show


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

    def build(self) -> Model.Geometry:
        b1 = Box(self.a, self.b, self.c)
        b2 = Box(self.b, self.c, self.d)
        print("show with or operator:", b1, b2)  # noqa: T201
        show / (b1, b2)  # ty: ignore[unsupported-operator]
        raise Exception("`show |` should exit early")  # noqa: TRY002
        return b1, b2
