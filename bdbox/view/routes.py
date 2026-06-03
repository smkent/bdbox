"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TextIO, cast

from cattrs.errors import BaseValidationError
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from bdbox.console import console, log
from bdbox.errors import InternalError
from bdbox.protocol import (
    Message,
    ParamOverridesMessage,
    ResetParamsMessage,
    SchemaMessage,
    SelectPresetMessage,
    TerminalSizeMessage,
    UpdateParamMessage,
    protocol_serializer,
)
from bdbox.runner.state import run_state
from bdbox.serializer import serializer

from .console import WebStream
from .state import ViewState

routes_router = APIRouter()


@dataclass
class ViewWebSocket(WebSocket):
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
class ConnectionManager:
    active: list[WebSocket] = field(default_factory=list, init=False)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: Message) -> None:
        msg_json = protocol_serializer.to_dict(message)
        log.debug("Sent %s (%d clients)", msg_json["type"], len(self.active))
        log.trace(json.dumps(msg_json, indent=4))
        for ws in list(self.active):
            try:
                await ws.send_json(msg_json)
            except Exception:  # noqa: BLE001, PERF203
                self.disconnect(ws)


manager = ConnectionManager()


_PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>bdbox</title>
  <link rel="icon" type="image/png" href="/static/favicon.png">
  <link rel="stylesheet" href="/static/app.css">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ overflow: hidden; background: #111; }}
  </style>
  <script>window.__BDBOX__ = {{"viewerPort": {viewer_port}}};</script>
  <script src="/static/app.js" defer></script>
</head>
<body>
  <div id="layout" style="width: 100%; height: 100vh;"></div>
</body>
</html>
"""


@routes_router.get("/", response_class=HTMLResponse)
async def shell(request: Request) -> str:
    return _PAGE_TEMPLATE.format(
        viewer_port=ViewState.get(request).viewer_port
    )


def _handle_client_message(
    view_websocket: ViewWebSocket, msg: Message, view_state: ViewState
) -> None:
    if isinstance(msg, TerminalSizeMessage):
        console.add_web_output(
            id(view_websocket.websocket),
            cast("TextIO", WebStream(view_state.msg_queue)),
            msg.cols,
        )
    elif isinstance(msg, UpdateParamMessage):
        view_state.param_overrides[msg.field] = msg.value
        view_state.rerender_event.set()
        log.debug(f"Parameter updated: {msg.field} = {msg.value}")
    elif isinstance(msg, SelectPresetMessage):
        if view_state.model_class:
            for preset in view_state.model_class.presets:
                if preset.name == msg.preset:
                    view_state.param_overrides.clear()
                    view_state.param_overrides.update(
                        {
                            name: serializer.unstructure(value)
                            for name, value in preset.values.items()
                        }
                    )
                    view_state.rerender_event.set()
                    log.debug(f"Preset selected: {preset.name}")
                    break
    elif isinstance(msg, ResetParamsMessage):
        view_state.param_overrides.clear()
        view_state.rerender_event.set()
        log.debug("Parameters reset")
    else:
        raise InternalError(f"Unable to handle message {msg}")


@routes_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    view_state = ViewState.get(websocket.app)
    await manager.connect(websocket)
    view_websocket = ViewWebSocket(websocket)
    try:
        if view_state.model_class:
            await view_websocket.send_message(
                SchemaMessage(
                    session_id=view_state.session_id,
                    schema=run_state.model_state.schema,
                    current_values=serializer.unstructure(
                        view_state.current_values
                    ),
                    model_running=run_state.model_state.model_running,
                    model_run_started=(
                        run_state.model_state.timer.started_at
                        if run_state.model_state.timer
                        else None
                    ),
                    model_info=run_state.model_state.model_name_info(),
                )
            )
        while True:
            if message := await view_websocket.receive_message():
                _handle_client_message(view_websocket, message, view_state)
                await view_websocket.send_message(
                    ParamOverridesMessage(
                        session_id=view_state.session_id,
                        param_overrides=dict(view_state.param_overrides),
                    )
                )
    except WebSocketDisconnect:
        console.remove_web_output(id(view_websocket))
        manager.disconnect(websocket)
