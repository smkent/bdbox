"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from bdbox.console import console
from bdbox.dispatch import dispatch
from bdbox.protocol import (
    ClientInfoMessage,
    ConnectedMessage,
    ModelDetailsMessage,
    ModelRunStatusMessage,
)
from bdbox.runner.state import run_state
from bdbox.view.console import WebStream
from bdbox.view.websocket import WebSocketConnection

from .templates import INDEX_TEMPLATE
from .websocket import WebSocketConnectionManager

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from queue import Queue

    from bdbox.protocol import ServerMessage

    from .state import ViewState


@dataclass
class App(FastAPI):
    STATIC_DIR = Path(__file__).parent / "static"

    view_state: ViewState
    session_id: UUID = field(default_factory=uuid4)
    msg_queues: dict[int, Queue[ServerMessage | None]] = field(
        default_factory=dict
    )
    viewer_port: int = 3939
    websocket_connections: WebSocketConnectionManager = field(
        default_factory=WebSocketConnectionManager, init=False
    )

    def __post_init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, lifespan=type(self).lifespan, **kwargs)
        dispatch.on_exit(self.stop_queues, name="Stop view App message queues")
        self.mount(
            "/static", StaticFiles(directory=self.STATIC_DIR), name="static"
        )
        self.include_router(self.endpoint_router)

    def enqueue(self, msg: ServerMessage) -> None:
        for msg_queue in self.msg_queues.values():
            msg_queue.put(msg)

    def stop_queues(self) -> None:
        for msg_queue in self.msg_queues.values():
            msg_queue.put(None)

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        try:
            yield
        finally:
            self.stop_queues()

    @cached_property
    def endpoint_router(self) -> APIRouter:
        routes_router = APIRouter()
        routes_router.get("/", response_class=HTMLResponse)(
            self.index_endpoint
        )
        routes_router.websocket("/ws")(self.websocket_endpoint)
        return routes_router

    async def index_endpoint(self) -> str:
        return INDEX_TEMPLATE.format(viewer_port=self.viewer_port)

    async def websocket_endpoint(self, websocket: WebSocket) -> None:
        await self.websocket_connections.connect(websocket)
        try:
            await self.handle_client_connection(websocket)
        except WebSocketDisconnect:
            console.remove_web_output(id(websocket))
            self.websocket_connections.disconnect(websocket)
            self.msg_queues.pop(id(websocket), None)

    async def _drain_queue(self, websocket: WebSocket, qq: Queue) -> None:
        while msg := await asyncio.to_thread(qq.get):
            try:
                await websocket.send_json(msg.to_dict())
            except Exception:  # noqa: BLE001, PERF203
                break

    async def handle_client_connection(self, websocket: WebSocket) -> None:
        view_websocket = WebSocketConnection(websocket)
        ws_id = id(websocket)
        webstream = WebStream()
        self.msg_queues[ws_id] = webstream.q
        send_task = asyncio.create_task(
            self._drain_queue(websocket, webstream.q)
        )
        try:
            await view_websocket.send_message(
                ConnectedMessage(session_id=self.session_id)
            )
            if self.view_state.model_class:
                await view_websocket.send_message(
                    ModelDetailsMessage(
                        schema=run_state.model_state.schema,
                        params=self.view_state.params,
                        model_info=run_state.model_state.model,
                    )
                )
                if timer := run_state.model_state.timer:
                    await view_websocket.send_message(
                        ModelRunStatusMessage.running(
                            started_at=timer.started_at
                        )
                    )
            while True:
                if message := await view_websocket.receive_message():
                    if isinstance(message, ClientInfoMessage):
                        console.add_web_output(
                            ws_id,
                            cast("TextIO", webstream),
                            message.terminal.cols,
                        )
                        webstream.q.put(
                            ModelDetailsMessage(params=self.view_state.params)
                        )
                        continue
                    self.view_state.handle_model_message(message)
                    webstream.q.put(
                        ModelDetailsMessage(params=self.view_state.params)
                    )
        finally:
            webstream.q.put(None)
            with suppress(asyncio.CancelledError):
                await send_task
