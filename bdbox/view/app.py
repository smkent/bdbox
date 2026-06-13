"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from queue import Queue
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
    ServerMessage,
)
from bdbox.runner.state import run_state

from .console import WebStream
from .templates import INDEX_TEMPLATE
from .websocket import WebSocketConnection, WebSocketConnectionManager

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from .state import ViewState


@dataclass
class App(FastAPI):
    STATIC_DIR = Path(__file__).parent / "static"

    view_state: ViewState
    session_id: UUID = field(default_factory=uuid4)
    msg_queue: Queue[ServerMessage | None] = field(default_factory=Queue)
    viewer_port: int = 3939
    websocket_connections: WebSocketConnectionManager = field(
        default_factory=WebSocketConnectionManager, init=False
    )

    def __post_init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, lifespan=type(self).lifespan, **kwargs)
        dispatch.on_exit(self.stop_queue, name="Stop view App message queue")
        self.mount(
            "/static", StaticFiles(directory=self.STATIC_DIR), name="static"
        )
        self.include_router(self.endpoint_router)

    def enqueue(self, msg: ServerMessage) -> None:
        self.msg_queue.put(msg)

    def stop_queue(self) -> None:
        self.msg_queue.put(None)

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        async def send_from_queue() -> None:
            while msg := await asyncio.to_thread(self.msg_queue.get):
                await self.websocket_connections.send(msg)

        task = asyncio.create_task(send_from_queue())
        try:
            yield
        finally:
            self.stop_queue()
            await task

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

    async def handle_client_connection(self, websocket: WebSocket) -> None:
        view_websocket = WebSocketConnection(websocket)
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
                    ModelRunStatusMessage.running(started_at=timer.started_at)
                )
        while True:
            if message := await view_websocket.receive_message():
                if isinstance(message, ClientInfoMessage):
                    console.add_web_output(
                        id(view_websocket.websocket),
                        cast("TextIO", WebStream(self.msg_queue)),
                        message.terminal.cols,
                    )
                else:
                    self.view_state.handle_model_message(message)
                await view_websocket.send_message(
                    ModelDetailsMessage(params=self.view_state.params)
                )
