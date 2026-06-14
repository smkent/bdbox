from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from functools import cached_property
from queue import Queue
from typing import TYPE_CHECKING, TextIO, cast

from cattrs.errors import BaseValidationError

from bdbox.console import log
from bdbox.protocol import BrowserMessage, ModelConsoleMessage, ServerMessage

if TYPE_CHECKING:
    from fastapi import WebSocket


@dataclass
class WebSocketStream:
    """Write-only stream that forwards text to the WebSocket message queue."""

    msg_queue: Queue[ServerMessage | None]

    def write(self, text: str) -> int:
        if text.strip():
            self.msg_queue.put(ModelConsoleMessage(text=text))
        return len(text)

    def flush(self) -> None:
        pass


@dataclass
class WebSocketConnection:
    websocket: WebSocket
    msg_queue: Queue[ServerMessage | None] = field(default_factory=Queue)

    async def drain_queue(self) -> None:
        while msg := await asyncio.to_thread(self.msg_queue.get):
            try:
                await self.websocket.send_json(msg.to_dict())
            except Exception:  # noqa: BLE001, PERF203
                break

    async def send_message(self, message: ServerMessage) -> None:
        msg_json = message.to_dict()
        if message.log_ok:
            log.debug("Sent %s", msg_json["type"])
            log.trace(json.dumps(msg_json, indent=4))
        return await self.websocket.send_json(msg_json)

    async def receive_message(self) -> BrowserMessage | None:
        try:
            data = await self.websocket.receive_json()
        except ValueError:
            return None
        log.debug("Received %s", data["type"])
        log.trace(json.dumps(data, indent=4))
        try:
            return BrowserMessage.from_dict(data)
        except (KeyError, TypeError, BaseValidationError):
            return None

    def stop(self) -> None:
        self.msg_queue.put(None)

    @cached_property
    def stream(self) -> TextIO:
        return cast("TextIO", WebSocketStream(msg_queue=self.msg_queue))
