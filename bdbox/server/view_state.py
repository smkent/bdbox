"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from queue import Queue
from threading import Event
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Request

from bdbox.errors import InternalError

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from bdbox.parameters.parameters import Params


@dataclass
class ViewState:
    rerender_event: Event = field(default_factory=Event, repr=False)
    viewer_port: int = 3939
    model_class: type[Params] | None = None
    msg_queue: Queue[dict[str, Any]] = field(default_factory=Queue)
    param_overrides: dict[str, Any] = field(default_factory=dict)
    current_values: dict[str, Any] = field(default_factory=dict)
    session_id: UUID = field(default_factory=uuid4)

    def enqueue(self, msg: dict[str, Any]) -> None:
        self.msg_queue.put({**msg, "session_id": str(self.session_id)})

    @classmethod
    def get(cls, obj: FastAPI | Request) -> Self:
        if isinstance(obj, Request):
            obj = obj.app
        if isinstance(obj, FastAPI):
            return obj.state.view_state
        raise InternalError(f"{cls.__name__} not found")
