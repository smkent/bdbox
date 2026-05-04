"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI

from .routes import manager, routes_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from .context import Context

_STOP = object()


async def _broadcast_loop(context: Context) -> None:
    while True:
        msg = await asyncio.to_thread(context.msg_queue.get)
        if msg is _STOP:
            break
        await manager.broadcast(msg)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    context: Context = app.state.context
    task = asyncio.create_task(_broadcast_loop(context))
    try:
        yield
    finally:
        context.msg_queue.put(_STOP)
        await task


class App(FastAPI):
    def __init__(self, context: Context, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, lifespan=_lifespan, **kwargs)
        self.state.context = context
        self.include_router(routes_router)
