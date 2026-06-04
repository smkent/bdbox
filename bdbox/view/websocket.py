from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cattrs.errors import BaseValidationError

from bdbox.console import log
from bdbox.protocol import (
    BrowserMessage,
    ServerMessage,
)

if TYPE_CHECKING:
    from fastapi import WebSocket


@dataclass
class WebSocketConnection:
    websocket: WebSocket

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


@dataclass
class WebSocketConnectionManager:
    connections: list[WebSocket] = field(default_factory=list, init=False)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.connections:
            self.connections.remove(ws)

    async def send(self, message: ServerMessage) -> None:
        msg_json = message.to_dict()
        if message.log_ok:
            log.debug(
                "Sent %s (%d clients)", message.type, len(self.connections)
            )
            log.trace(json.dumps(msg_json, indent=4))
        for ws in list(self.connections):
            try:
                await ws.send_json(msg_json)
            except Exception:  # noqa: BLE001, PERF203
                self.disconnect(ws)
