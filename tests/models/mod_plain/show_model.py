from dataclasses import dataclass

from bdbox import show


@dataclass
class Box:
    x: float
    y: float
    z: float


boxes = Box(10, 20, 30), Box(30, 40, 50)
print("show with or operator:", boxes)  # noqa: T201
show / boxes  # ty: ignore[unsupported-operator]
raise Exception("`show |` should exit early")  # noqa: TRY002
show(boxes)
