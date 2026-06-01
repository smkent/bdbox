"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes import manager, routes_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from .state import ViewState

_STATIC_DIR = Path(__file__).parent / "static"


async def _broadcast_loop(view_state: ViewState) -> None:
    while True:
        if (msg := await asyncio.to_thread(view_state.msg_queue.get)) is None:
            break
        await manager.broadcast(msg)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    view_state: ViewState = app.state.view_state
    task = asyncio.create_task(_broadcast_loop(view_state))
    try:
        yield
    finally:
        view_state.stop_queue()
        await task


class App(FastAPI):
    def __init__(
        self, view_state: ViewState, *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, lifespan=_lifespan, **kwargs)
        self.state.view_state = view_state
        self.mount(
            "/static", StaticFiles(directory=_STATIC_DIR), name="static"
        )
        self.include_router(routes_router)
