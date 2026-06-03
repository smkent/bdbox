"""Console output capture for WebSocket streaming."""

from __future__ import annotations

import queue
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bdbox.protocol import ConsoleMessage

if TYPE_CHECKING:
    from bdbox.protocol import Message


@dataclass
class WebStream:
    """Write-only stream that forwards text to the WebSocket message queue."""

    q: queue.Queue[Message | None] = field(default_factory=queue.Queue)

    def write(self, text: str) -> int:
        if text.strip():
            self.q.put(ConsoleMessage(text=text))
        return len(text)

    def flush(self) -> None:
        pass
