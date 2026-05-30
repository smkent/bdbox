"""Console output capture for WebSocket streaming."""

from __future__ import annotations

import queue
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass
class WebStream:
    """Write-only stream that forwards text to the WebSocket message queue."""

    q: queue.Queue[Mapping[str, Any] | object] = field(
        default_factory=queue.Queue
    )

    def write(self, text: str) -> int:
        if text.strip():
            self.q.put({"type": "console", "stream": "stdout", "text": text})
        return len(text)

    def flush(self) -> None:
        pass
