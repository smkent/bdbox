from __future__ import annotations

from enum import Enum, auto

from tests.models.utils import build123d

assert build123d

from build123d import Box  # noqa: E402

from bdbox import Params, show  # noqa: E402


class ExportTypes(Enum):
    solids = auto()
    edges = auto()
    both = auto()


class P(Params):
    select: ExportTypes = ExportTypes.solids


b1 = Box(10, 20, 30)
if P.select == ExportTypes.edges:
    show(b1.edges())
elif P.select == ExportTypes.both:
    show(b1, b1.edges())
else:
    show(b1)
