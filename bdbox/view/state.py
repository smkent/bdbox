"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, replace
from queue import Queue
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Request

from bdbox.dispatch import Event, dispatch
from bdbox.errors import InternalError

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from bdbox.model.parameters import Params
    from bdbox.protocol import Message, MessageWithSessionID


@dataclass
class ViewState:
    rerender_event: Event = field(
        default_factory=lambda: Event(name="rerender_event"), repr=False
    )
    viewer_port: int = 3939
    model_class: type[Params] | None = None
    msg_queue: Queue[Message | None] = field(default_factory=Queue)
    param_overrides: dict[str, Any] = field(default_factory=dict)
    current_values: dict[str, Any] = field(default_factory=dict)
    session_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        dispatch.on_exit(self.stop_queue, name="Stop ViewState message queue")

    def enqueue(self, msg: MessageWithSessionID) -> None:
        self.msg_queue.put(replace(msg, session_id=self.session_id))

    def stop_queue(self) -> None:
        self.msg_queue.put(None)

    @classmethod
    def get(cls, obj: FastAPI | Request) -> Self:
        if isinstance(obj, Request):
            obj = obj.app
        if isinstance(obj, FastAPI):
            return obj.state.view_state
        raise InternalError(f"{cls.__name__} not found")
