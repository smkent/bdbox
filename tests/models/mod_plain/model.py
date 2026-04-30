from dataclasses import dataclass


@dataclass
class Box:
    x: float
    y: float
    z: float


boxes = Box(10, 20, 30), Box(30, 40, 50)
print("Boxes:", boxes)  # noqa: T201
