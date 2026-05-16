from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import cached_property


def get_time() -> float:
    return time.monotonic()


@dataclass
class Timer:
    start: float = field(default_factory=get_time, repr=False)

    @property
    def started_at(self) -> datetime:
        return datetime.now(timezone.utc) - timedelta(
            seconds=self.elapsed / 1000
        )

    @property
    def stopped(self) -> bool:
        return "end" in self.__dict__

    @property
    def elapsed(self) -> float:
        if self.stopped:
            return self.end
        return (get_time() - self.start) * 1000

    @cached_property
    def end(self) -> int:
        return round(self.elapsed)

    @cached_property
    def end_str(self) -> str:
        return self._format(self.end)

    def _format(self, ms: float) -> str:
        if ms < 1000:
            return f"{int(ms)}ms"
        if ms < 10_000:
            return f"{ms / 1000:.1f}s"
        total_s = int(ms / 1000)
        if total_s < 60:
            return f"{total_s}s"
        m, s = divmod(total_s, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        parts = [f"{d}d"] if d else []
        if h or d:
            parts.append(f"{h}h")
        parts.append(f"{m}m")
        parts.append(f"{s}s")
        return " ".join(parts)

    def __str__(self) -> str:
        return self._format(self.elapsed)
