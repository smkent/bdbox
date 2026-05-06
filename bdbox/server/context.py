"""bdbox parameter panel FastAPI app."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from queue import Queue
from threading import Event
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request

from bdbox.errors import Error

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from bdbox.parameters.parameters import Params


@dataclass
class Context:
    rerender_event: Event = field(default_factory=Event, repr=False)
    viewer_port: int = 3939
    model_class: type[Params] | None = None
    msg_queue: Queue[dict[str, Any]] = field(default_factory=Queue)
    param_overrides: dict[str, Any] = field(default_factory=dict)
    current_values: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def get(cls, obj: FastAPI | Request) -> Self:
        if isinstance(obj, Request):
            obj = obj.app
        if isinstance(obj, FastAPI):
            return obj.state.context
        raise Error(f"{cls.__name__} not found")
