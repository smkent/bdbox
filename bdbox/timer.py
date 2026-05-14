from __future__ import annotations

import time
from dataclasses import dataclass, field
from functools import cached_property


@dataclass
class Timer:
    start: float = field(
        default_factory=time.monotonic, init=False, repr=False
    )

    @property
    def elapsed(self) -> float:
        return (time.monotonic() - self.start) * 1000

    @cached_property
    def end(self) -> int:
        return int(self.elapsed)
