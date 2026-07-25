from __future__ import annotations

from enum import Enum, auto
from typing import Any

from tests.models.utils import build123d

assert build123d

from build123d import Box  # noqa: E402

from bdbox import Model  # noqa: E402


class ExportTypes(Enum):
    solids = auto()
    edges = auto()
    both = auto()


class ExportModel(Model):
    select: ExportTypes = ExportTypes.solids

    def build(self) -> Any:
        b1 = Box(10, 20, 30)
        if self.select == ExportTypes.edges:
            return b1.edges()
        if self.select == ExportTypes.both:
            return b1, b1.edges()
        return b1
