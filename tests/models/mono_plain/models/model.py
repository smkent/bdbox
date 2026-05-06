from __future__ import annotations

from tests.models.mono_plain.misc.constants import Defaults
from tests.models.utils import build123d

assert build123d

from build123d import Box  # noqa: E402

boxes = (
    Box(Defaults.A, Defaults.B, Defaults.C),
    Box(Defaults.B, Defaults.C, Defaults.D),
)

print("Box count:", len(boxes))  # noqa: T201
