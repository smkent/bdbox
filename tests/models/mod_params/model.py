from dataclasses import dataclass

from bdbox import Float, Int, Params, show


@dataclass
class Box:
    x: float
    y: float
    z: float


class P(Params):
    a: float = 2.5
    b: int = 3
    c = Int(5, min=1, max=10)
    d = Float(5.0, min=1.0, max=10.0)


b1 = Box(P.a, P.b, P.c)
b2 = Box(P.b, P.c, P.d)
print("b1", b1)  # noqa: T201
print("b2", b2)  # noqa: T201
show(b1, b2)  # ty: ignore[invalid-argument-type]
