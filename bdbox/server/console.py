"""Console output capture for WebSocket streaming."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import queue
    from collections.abc import Iterator


class _TeeStream:
    def __init__(
        self, original: Any, q: queue.Queue[dict[str, Any]], stream: str
    ) -> None:
        self._original = original
        self._queue = q
        self._stream = stream

    def write(self, text: str) -> None:
        self._original.write(text)
        if text.strip():
            self._queue.put(
                {"type": "console", "stream": self._stream, "text": text}
            )

    def flush(self) -> None:
        self._original.flush()


@contextmanager
def tee_stderr(q: queue.Queue[dict[str, Any]]) -> Iterator[None]:
    original = sys.stderr
    sys.stderr = _TeeStream(original, q, "stderr")  # type: ignore[assignment]
    try:
        yield
    finally:
        sys.stderr = original
