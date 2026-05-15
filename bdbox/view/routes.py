"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, TextIO, cast

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from bdbox.console import console, log
from bdbox.model.state import model_state
from bdbox.serializer import Serializer

from .console import WebStream
from .state import ViewState

routes_router = APIRouter()
serializer = Serializer()


@dataclass
class ConnectionManager:
    active: list[WebSocket] = field(default_factory=list, init=False)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active.remove(ws)

    async def broadcast(self, message: dict) -> None:
        for ws in list(self.active):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001, PERF203
                self.disconnect(ws)


manager = ConnectionManager()


_PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>bdbox</title>
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
    websocket: WebSocket, data: dict[str, Any], view_state: ViewState
) -> None:
    msg_type = data.get("type")
    if msg_type == "terminal_size":
        cols = int(data.get("cols", 80))
        console.add_web_output(
            id(websocket),
            cast("TextIO", WebStream(view_state.msg_queue)),
            cols,
        )
    elif msg_type == "update_param":
        view_state.param_overrides[data["field"]] = data["value"]
        view_state.rerender_event.set()
        log.debug(f"Parameter updated: {data['field']} = {data['value']}")
    elif msg_type == "select_preset":
        if view_state.model_class:
            for preset in view_state.model_class.presets:
                if preset.name == data["preset"]:
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
    elif msg_type == "reset_params":
        view_state.param_overrides.clear()
        view_state.rerender_event.set()
        log.debug("Parameters reset")


@routes_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    view_state = ViewState.get(websocket.app)
    await manager.connect(websocket)
    try:
        if view_state.model_class:
            msg = {
                "type": "schema",
                "schema": serializer.json_schema(view_state.model_class),
                "current_values": view_state.current_values,
                "session_id": str(view_state.session_id),
                "model_running": model_state.model_running,
                "model_info": model_state.model_name_info(),
            }
            log.debug("Sent %s", msg["type"])
            log.trace(json.dumps(msg, indent=4))
            await websocket.send_json(msg)
        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:
                continue
            log.debug("Received %s", data["type"])
            log.trace(json.dumps(data, indent=4))
            try:
                _handle_client_message(websocket, data, view_state)
            except (KeyError, TypeError):
                continue
            reply = {
                "type": "param_overrides",
                "param_overrides": dict(view_state.param_overrides),
            }
            log.debug("Sent %s", reply["type"])
            log.trace(json.dumps(reply, indent=4))
            await websocket.send_json(reply)
    except WebSocketDisconnect:
        console.remove_web_output(id(websocket))
        manager.disconnect(websocket)
