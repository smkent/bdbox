from __future__ import annotations

from enum import Enum, auto

from tests.models.utils import build123d

assert build123d

from build123d import Box  # noqa: E402

from bdbox import Params, show  # noqa: E402


class ExportTypes(Enum):
    solids = auto()
    vertices = auto()
    edges = auto()
    faces = auto()
    nothing = auto()
    solids_and_mixed = auto()


class P(Params):
    select: ExportTypes = ExportTypes.solids


if P.select != ExportTypes.nothing:
    b1 = Box(10, 20, 30)
    b2 = Box(5, 10, 15)
    if P.select == ExportTypes.vertices:
        show(b1.vertices())
    elif P.select == ExportTypes.edges:
        show(b1.edges())
    elif P.select == ExportTypes.faces:
        show(b1.faces())
    elif P.select == ExportTypes.solids_and_mixed:
        show(b1, b2, b1.edges())
    else:
        show(b1, b2)
