from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cattrs.errors import BaseValidationError

from bdbox.console import log
from bdbox.protocol import Message, protocol_serializer

if TYPE_CHECKING:
    from fastapi import WebSocket


@dataclass
class WebSocketConnection:
    websocket: WebSocket

    async def send_message(self, message: Message) -> None:
        msg_json = protocol_serializer.to_dict(message)
        log.debug("Sent %s", msg_json["type"])
        log.trace(json.dumps(msg_json, indent=4))
        return await self.websocket.send_json(msg_json)

    async def receive_message(self) -> Message | None:
        try:
            data = await self.websocket.receive_json()
        except ValueError:
            return None
        log.debug("Received %s", data["type"])
        log.trace(json.dumps(data, indent=4))
        try:
            return protocol_serializer.from_dict(data)
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

    async def send(self, message: Message) -> None:
        log.debug("Sent %s (%d clients)", message.type, len(self.connections))
        msg_json = protocol_serializer.to_dict(message)
        log.trace(json.dumps(msg_json, indent=4))
        for ws in list(self.connections):
            try:
                await ws.send_json(msg_json)
            except Exception:  # noqa: BLE001, PERF203
                self.disconnect(ws)
