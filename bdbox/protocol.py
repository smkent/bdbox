from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal
from uuid import UUID

import cattrs
import cattrs.strategies

from bdbox.errors import InternalError


@dataclass
class ProtocolMessage:
    type: ClassVar[str] = ""

    def __init_subclass__(cls, *, abstract: bool = False) -> None:
        if not abstract and not cls.type:
            raise InternalError(f"{cls} is missing type property value")


@dataclass
class ProtocolMessageWithSessionID(ProtocolMessage, abstract=True):
    session_id: UUID


@dataclass
class TerminalSizeMessage(ProtocolMessage):
    type: ClassVar[str] = "terminal_size"
    cols: int = 80


@dataclass
class ConsoleMessage(ProtocolMessage):
    type: ClassVar[str] = "console"
    text: str
    stream: Literal["stdout"] = "stdout"


@dataclass
class UpdateParamMessage(ProtocolMessage):
    type: ClassVar[str] = "update_param"
    field: str
    value: Any


@dataclass
class SelectPresetMessage(ProtocolMessage):
    type: ClassVar[str] = "select_preset"
    preset: str


@dataclass
class ResetParamsMessage(ProtocolMessage):
    type: ClassVar[str] = "reset_params"


@dataclass
class ModelNameInfo:
    file: str | None = None
    module: str | None = None
    cls: str | None = None


@dataclass
class SchemaMessage(ProtocolMessageWithSessionID):
    type: ClassVar[str] = "schema"
    schema: dict[str, Any] | None = None
    current_values: dict[str, Any] = field(default_factory=dict)
    model_running: bool | None = None
    model_run_started: str | None = None
    model_info: ModelNameInfo = field(default_factory=ModelNameInfo)


@dataclass
class ParamOverridesMessage(ProtocolMessageWithSessionID):
    type: ClassVar[str] = "param_overrides"
    param_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunStartMessage(ProtocolMessageWithSessionID):
    type: ClassVar[str] = "run_start"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunOKMessage(ProtocolMessageWithSessionID):
    type: ClassVar[str] = "run_ok"
    elapsed_ms: str
    current_values: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunErrorMessage(ProtocolMessageWithSessionID):
    type: ClassVar[str] = "run_error"
    elapsed_ms: str


Message = (
    TerminalSizeMessage
    | ConsoleMessage
    | UpdateParamMessage
    | SelectPresetMessage
    | ResetParamsMessage
    | SchemaMessage
    | ParamOverridesMessage
    | RunStartMessage
    | RunOKMessage
    | RunErrorMessage
)


def _tag(cls: type) -> str:
    if not issubclass(cls, ProtocolMessage):
        raise InternalError(f"{cls} is not a ProtocolMessage")
    return cls.type


class ProtocolConverter(cattrs.Converter):
    def __init__(self) -> None:
        super().__init__()
        self.register_structure_hook(UUID, lambda val, _: UUID(val))
        self.register_unstructure_hook(UUID, str)
        cattrs.strategies.configure_tagged_union(
            Message, self, tag_name="type", tag_generator=_tag
        )

    def to_dict(self, obj: Any) -> Any:
        return self.unstructure(obj=obj, unstructure_as=Message)

    def from_dict(self, obj: Any) -> Message:
        return self.structure(obj=obj, cl=Message)  # ty: ignore[invalid-argument-type]


protocol_serializer = ProtocolConverter()
