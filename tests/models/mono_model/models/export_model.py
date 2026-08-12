from __future__ import annotations

from enum import Enum, auto
from typing import Any

from tests.models.utils import build123d

assert build123d

from build123d import Box  # noqa: E402

from bdbox import Model  # noqa: E402


class ExportTypes(Enum):
    solids = auto()
    vertices = auto()
    edges = auto()
    faces = auto()
    nothing = auto()
    solids_and_mixed = auto()


class ExportModel(Model):
    select: ExportTypes = ExportTypes.solids

    def build(self) -> Any:
        b1 = Box(10, 20, 30)
        b2 = Box(5, 10, 15)
        if self.select == ExportTypes.nothing:
            return None
        if self.select == ExportTypes.vertices:
            return b1.edges().vertices()
        if self.select == ExportTypes.edges:
            return b1.edges()
        if self.select == ExportTypes.faces:
            return b1.faces()
        if self.select == ExportTypes.solids_and_mixed:
            return b1, b2, b1.edges()
        return b1, b2
