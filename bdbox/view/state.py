"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

from dataclasses import dataclass, field
from queue import Queue
from typing import TYPE_CHECKING, Any, TextIO, cast
from uuid import UUID, uuid4

from bdbox.console import console, log
from bdbox.dispatch import Event, dispatch
from bdbox.errors import InternalError
from bdbox.protocol import (
    ConnectedMessage,
    ModelDetailsMessage,
    ParamOverridesMessage,
    ResetParamsMessage,
    SelectPresetMessage,
    TerminalSizeMessage,
    UpdateParamMessage,
)
from bdbox.runner.state import run_state
from bdbox.serializer import serializer

from .console import WebStream
from .websocket import WebSocketConnection

if TYPE_CHECKING:
    from fastapi import WebSocket

    from bdbox.model.parameters import Params
    from bdbox.protocol import BrowserMessage, ServerMessage


@dataclass
class ViewState:
    rerender_event: Event = field(
        default_factory=lambda: Event(name="rerender_event"), repr=False
    )
    viewer_port: int = 3939
    model_class: type[Params] | None = None
    msg_queue: Queue[ServerMessage | None] = field(default_factory=Queue)
    param_overrides: dict[str, Any] = field(default_factory=dict)
    current_values: dict[str, Any] = field(default_factory=dict)
    session_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        dispatch.on_exit(self.stop_queue, name="Stop ViewState message queue")

    def enqueue(self, msg: ServerMessage) -> None:
        self.msg_queue.put(msg)

    def stop_queue(self) -> None:
        self.msg_queue.put(None)

    async def handle_client_connection(self, websocket: WebSocket) -> None:
        view_websocket = WebSocketConnection(websocket)
        await view_websocket.send_message(
            ConnectedMessage(session_id=self.session_id)
        )
        if self.model_class:
            await view_websocket.send_message(
                ModelDetailsMessage(
                    schema=run_state.model_state.schema,
                    current_values=serializer.unstructure(self.current_values),
                    model_running=run_state.model_state.model_running,
                    model_run_started=(
                        run_state.model_state.timer.started_at
                        if run_state.model_state.timer
                        else None
                    ),
                    model_info=run_state.model_state.model,
                )
            )
        while True:
            if message := await view_websocket.receive_message():
                self.handle_client_message(view_websocket, message)
                await view_websocket.send_message(
                    ParamOverridesMessage(
                        param_overrides=dict(self.param_overrides)
                    )
                )

    def handle_client_message(
        self, view_websocket: WebSocketConnection, msg: BrowserMessage
    ) -> None:
        if isinstance(msg, TerminalSizeMessage):
            console.add_web_output(
                id(view_websocket.websocket),
                cast("TextIO", WebStream(self.msg_queue)),
                msg.cols,
            )
        elif isinstance(msg, UpdateParamMessage):
            self.param_overrides[msg.field] = msg.value
            self.rerender_event.set()
            log.debug(f"Parameter updated: {msg.field} = {msg.value}")
        elif isinstance(msg, SelectPresetMessage):
            if self.model_class:
                for preset in self.model_class.presets:
                    if preset.name == msg.preset:
                        self.param_overrides.clear()
                        self.param_overrides.update(
                            {
                                name: serializer.unstructure(value)
                                for name, value in preset.values.items()
                            }
                        )
                        self.rerender_event.set()
                        log.debug(f"Preset selected: {preset.name}")
                        break
        elif isinstance(msg, ResetParamsMessage):
            self.param_overrides.clear()
            self.rerender_event.set()
            log.debug("Parameters reset")
        else:
            raise InternalError(f"Unable to handle message {msg}")
