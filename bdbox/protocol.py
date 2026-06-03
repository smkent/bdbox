from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from typing import Any, ClassVar, Literal
from uuid import UUID

import cattrs
import cattrs.strategies

from bdbox.errors import InternalError


@dataclass
class Message:
    type: ClassVar[str] = ""

    def __post_init__(self) -> None:
        if not self.type:
            raise InternalError(f"{self} is missing type property value")

    def __init_subclass__(cls, *, abstract: bool = False) -> None:
        if not abstract and not cls.type:
            raise InternalError(f"{cls} is missing type property value")


@dataclass
class MessageWithSessionID(Message, abstract=True):
    session_id: UUID | None = field(default=None, kw_only=True)


@dataclass
class TerminalSizeMessage(Message):
    type: ClassVar[str] = "terminal_size"
    cols: int = 80


@dataclass
class ConsoleMessage(Message):
    type: ClassVar[str] = "console"
    text: str
    stream: Literal["stdout"] = "stdout"


@dataclass
class UpdateParamMessage(Message):
    type: ClassVar[str] = "update_param"
    field: str
    value: Any


@dataclass
class SelectPresetMessage(Message):
    type: ClassVar[str] = "select_preset"
    preset: str


@dataclass
class ResetParamsMessage(Message):
    type: ClassVar[str] = "reset_params"


@dataclass
class ModelNameInfo:
    file: str | None = None
    module: str | None = None
    cls: str | None = None


@dataclass
class SchemaMessage(MessageWithSessionID):
    type: ClassVar[str] = "schema"
    schema: dict[str, Any] | None = None
    current_values: dict[str, Any] = field(default_factory=dict)
    model_running: bool | None = None
    model_run_started: datetime | None = None
    model_info: ModelNameInfo = field(default_factory=ModelNameInfo)


@dataclass
class ParamOverridesMessage(MessageWithSessionID):
    type: ClassVar[str] = "param_overrides"
    param_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunStartMessage(MessageWithSessionID):
    type: ClassVar[str] = "run_start"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunOKMessage(MessageWithSessionID):
    type: ClassVar[str] = "run_ok"
    elapsed_ms: str
    current_values: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunErrorMessage(MessageWithSessionID):
    type: ClassVar[str] = "run_error"
    elapsed_ms: str


class ProtocolConverter(cattrs.Converter):
    def __init__(self) -> None:
        super().__init__()
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
                tag_generator=lambda cls: cls.type,
            ),
        )

    def to_dict(self, obj: Any) -> Any:
        return self.unstructure(obj=obj, unstructure_as=Message)

    def from_dict(self, obj: Any) -> Message:
        return self.structure(obj=obj, cl=Message)


protocol_serializer = ProtocolConverter()
