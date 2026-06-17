"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any
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

from .templates import INDEX_TEMPLATE
from .websocket import WebSocketConnection

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bdbox.protocol import ServerMessage
    from bdbox.view.state import ViewState


@dataclass
class ViewServerApp(FastAPI):
    STATIC_DIR = Path(__file__).parent / "static"

    view_state: ViewState
    session_id: UUID = field(default_factory=uuid4)
    connections: dict[int, WebSocketConnection] = field(default_factory=dict)
    ocp_cad_viewer_port: int = 3939

    def __post_init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, lifespan=type(self).lifespan, **kwargs)
        dispatch.on_exit(self.stop, name="Stop view App message queues")
        self.mount(
            "/static", StaticFiles(directory=self.STATIC_DIR), name="static"
        )
        self.include_router(self.endpoint_router)

    def enqueue(self, msg: ServerMessage) -> None:
        for connection in self.connections.values():
            connection.msg_queue.put(msg)

    def stop(self) -> None:
        for connection in self.connections.values():
            connection.stop()

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        try:
            yield
        finally:
            self.stop()

    @cached_property
    def endpoint_router(self) -> APIRouter:
        routes_router = APIRouter()
        routes_router.get("/", response_class=HTMLResponse)(
            self.index_endpoint
        )
        routes_router.websocket("/ws")(self.websocket_endpoint)
        return routes_router

    async def index_endpoint(self) -> str:
        return INDEX_TEMPLATE.format(
            ocp_cad_viewer_port=self.ocp_cad_viewer_port
        )

    async def websocket_endpoint(self, websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            await self.handle_client_connection(websocket)
        except WebSocketDisconnect:
            console.remove_web_output(id(websocket))
            self.connections.pop(id(websocket), None)

    async def handle_client_connection(self, websocket: WebSocket) -> None:
        connection = WebSocketConnection(websocket)
        ws_id = id(websocket)
        self.connections[ws_id] = connection
        send_task = asyncio.create_task(connection.drain_queue())
        try:
            await connection.send_message(
                ConnectedMessage(session_id=self.session_id)
            )
            if self.view_state.model_class:
                await connection.send_message(
                    ModelDetailsMessage(
                        schema=run_state.model_state.schema,
                        params=self.view_state.params,
                        model_info=run_state.model_state.model,
                    )
                )
                if timer := run_state.model_state.timer:
                    await connection.send_message(
                        ModelRunStatusMessage.running(
                            started_at=timer.started_at
                        )
                    )
            while True:
                if message := await connection.receive_message():
                    if isinstance(message, ClientInfoMessage):
                        console.add_web_output(
                            ws_id, connection.stream, message.terminal.cols
                        )
                        connection.msg_queue.put(
                            ModelDetailsMessage(params=self.view_state.params)
                        )
                        continue
                    self.view_state.handle_model_message(message)
                    connection.msg_queue.put(
                        ModelDetailsMessage(params=self.view_state.params)
                    )
        finally:
            connection.stop()
            with suppress(asyncio.CancelledError):
                await send_task
