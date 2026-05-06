"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from bdbox.parameters.serializer import Serializer

from .context import Context

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

    async def broadcast(self, message: dict) -> None:  # type: ignore[type-arg]
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
    return _PAGE_TEMPLATE.format(viewer_port=Context.get(request).viewer_port)


def _handle_client_message(data: dict[str, Any], context: Context) -> None:
    msg_type = data.get("type")
    if msg_type == "update_param":
        context.param_overrides[data["field"]] = data["value"]
        context.rerender_event.set()
    elif msg_type == "select_preset":
        if context.model_class:
            for preset in context.model_class.presets:
                if preset.name == data["preset"]:
                    context.param_overrides.clear()
                    context.param_overrides.update(
                        {
                            name: serializer.unstructure(value)
                            for name, value in preset.values.items()
                        }
                    )
                    context.rerender_event.set()
                    break
    elif msg_type == "reset_params":
        context.param_overrides.clear()
        context.rerender_event.set()


@routes_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    context = Context.get(websocket.app)
    await manager.connect(websocket)
    try:
        if context.model_class:
            await websocket.send_json(
                {
                    "type": "schema",
                    "schema": context.model_class.schema(),
                    "current_values": context.current_values,
                }
            )
        while True:
            data = await websocket.receive_json()
            _handle_client_message(data, context)
            await websocket.send_json(
                {
                    "type": "param_overrides",
                    "param_overrides": dict(context.param_overrides),
                }
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
