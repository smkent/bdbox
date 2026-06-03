"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from bdbox.console import console

from .templates import INDEX_TEMPLATE
from .websocket import WebSocketConnectionManager

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from .state import ViewState


@dataclass
class App(FastAPI):
    STATIC_DIR = Path(__file__).parent / "static"

    view_state: ViewState
    websocket_connections: WebSocketConnectionManager = field(
        default_factory=WebSocketConnectionManager, init=False
    )

    def __post_init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, lifespan=type(self).lifespan, **kwargs)
        self.mount(
            "/static", StaticFiles(directory=self.STATIC_DIR), name="static"
        )
        self.include_router(self.endpoint_router)

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        async def send_from_queue() -> None:
            while msg := await asyncio.to_thread(
                self.view_state.msg_queue.get
            ):
                await self.websocket_connections.send(msg)

        task = asyncio.create_task(send_from_queue())
        try:
            yield
        finally:
            self.view_state.stop_queue()
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
        return INDEX_TEMPLATE.format(viewer_port=self.view_state.viewer_port)

    async def websocket_endpoint(self, websocket: WebSocket) -> None:
        await self.websocket_connections.connect(websocket)
        try:
            await self.view_state.handle_client_connection(websocket)
        except WebSocketDisconnect:
            console.remove_web_output(id(websocket))
            self.websocket_connections.disconnect(websocket)
