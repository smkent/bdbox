from __future__ import annotations

from build123d import BaseSketchObject, BuildSketch, Circle, Mode


class CustomCircle(BaseSketchObject):
    def __init__(self, radius: float, mode: Mode = Mode.ADD) -> None:
        with BuildSketch() as sk:
            Circle(radius)
        super().__init__(obj=sk.sketch, mode=mode)
