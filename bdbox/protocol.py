from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import partial
from typing import (
    Annotated,
    Any,
    ClassVar,
    TypeVar,
    overload,
)
from uuid import UUID

import cattrs.strategies
from cattrs.gen import override

from bdbox.converter import Converter
from bdbox.errors import InternalError

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


def _bdbox_version() -> str:
    from bdbox import version  # noqa: PLC0415

    return version


@dataclass
class VersionInfo:
    PROTOCOL_REVISION: ClassVar[int] = 1

    bdbox: str = field(default_factory=_bdbox_version)
    protocol: int = field(default=PROTOCOL_REVISION)


@dataclass
class ModelDisplayInfo:
    filename: str | None = None
    module_name: str | None = None
    class_name: str | None = None


@dataclass
class TerminalInfo:
    cols: int = 80
    rows: int | None = None


@dataclass
class Message:
    type: ClassVar[str] = ""
    log_ok: ClassVar[bool] = True

    def __post_init__(self) -> None:
        if not self.type:
            raise InternalError(f"{self} is missing type property value")

    def __init_subclass__(
        cls,
        *,
        type: str | None = None,  # noqa: A002
        log_ok: bool | None = None,
    ) -> None:
        cls.type = type or cls.type
        cls.log_ok = log_ok if log_ok is not None else cls.log_ok

    def to_dict(self) -> dict[str, object]:
        return protocol_serializer.unstructure(obj=self)

    @classmethod
    def from_dict(cls, obj: dict[str, object]) -> Self:
        return protocol_serializer.structure(obj=obj, cl=cls)


MessageT = TypeVar("MessageT", bound=Message)


@dataclass
class ModelMessage(Message):
    pass


@dataclass
class BrowserMessage(Message):
    pass


@dataclass
class BrowserModelMessage(BrowserMessage, ModelMessage):
    pass


@dataclass
class ServerMessage(Message):
    pass


@dataclass
class ServerModelMessage(ServerMessage, ModelMessage):
    pass


@dataclass
class ConnectedMessage(ServerMessage, type="hello"):
    session_id: UUID | None = field(default=None, kw_only=True)
    version: VersionInfo = field(default_factory=VersionInfo)


@dataclass
class ClientInfoMessage(BrowserMessage, type="client.info"):
    terminal: TerminalInfo = field(default_factory=TerminalInfo)


@dataclass
class ModelResetParamsMessage(BrowserModelMessage, type="model.reset_params"):
    pass


@dataclass
class ModelSetParamMessage(BrowserModelMessage, type="model.set_param"):
    field: str
    value: Any


@dataclass
class ModelSetPresetMessage(BrowserModelMessage, type="model.set_preset"):
    preset: str


@dataclass
class ModelConsoleMessage(
    ServerModelMessage, type="model.console", log_ok=False
):
    text: str


@dataclass
class ModelParamsState:
    values: dict[str, Any] = field(default_factory=dict)
    overrides: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelDetailsMessage(ServerModelMessage, type="model.details"):
    schema: Annotated[
        dict[str, Any] | None, override(omit_if_default=True)
    ] = None
    model_info: Annotated[
        ModelDisplayInfo | None, override(omit_if_default=True)
    ] = None
    params: Annotated[
        ModelParamsState | None, override(omit_if_default=True)
    ] = None


@dataclass
class ModelRunStatusMessage(ServerModelMessage, type="model.status"):
    class Status(Enum):
        RUNNING = "running"
        DONE = "done"
        ERROR = "error"

    status: ModelRunStatusMessage.Status = field(kw_only=True)
    started_at: Annotated[datetime | None, override(omit_if_default=True)] = (
        None
    )
    elapsed_ms: Annotated[int | None, override(omit_if_default=True)] = None

    @classmethod
    def running(cls, started_at: datetime, **kwargs: Any) -> Self:
        return cls(status=cls.Status.RUNNING, started_at=started_at, **kwargs)

    @classmethod
    def done(cls, elapsed_ms: int, **kwargs: Any) -> Self:
        return cls(status=cls.Status.DONE, elapsed_ms=elapsed_ms, **kwargs)

    @classmethod
    def error(cls, elapsed_ms: int, **kwargs: Any) -> Self:
        return cls(status=cls.Status.ERROR, elapsed_ms=elapsed_ms, **kwargs)


class ProtocolConverter(Converter):
    def to_dict(self, obj: Message) -> dict[str, object]:
        return self.unstructure(obj=obj, unstructure_as=Message)

    @overload
    def from_dict(self, obj: dict[str, object]) -> Message: ...
    @overload
    def from_dict(
        self, obj: dict[str, object], cl: type[MessageT]
    ) -> MessageT: ...
    def from_dict(
        self, obj: dict[str, object], cl: type[Message] = Message
    ) -> Message:
        return self.structure(obj=obj, cl=cl)

    def register_hooks(self) -> None:
        super().register_hooks()
        self.register_structure_hook(UUID, lambda val, _: UUID(val))
        self.register_structure_hook(
            datetime, lambda val, _: datetime.fromisoformat(val)
        )
        self.register_unstructure_hook(UUID, str)
        self.register_unstructure_hook(datetime, lambda val: val.isoformat())
        cattrs.strategies.include_subclasses(
            Message,
            self,
            union_strategy=partial(
                cattrs.strategies.configure_tagged_union,
                tag_name="type",
                tag_generator=lambda target: target.type,
            ),
        )


protocol_serializer = ProtocolConverter()
