from __future__ import annotations

import sys
from dataclasses import MISSING, dataclass, field, make_dataclass
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Generic,
    Literal,
    Protocol,
    TypeVar,
    cast,
    overload,
)

import tyro

from bdbox.actions.field import ActionField
from bdbox.actions.run import RunAction

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Sequence


T = TypeVar("T", bound="CLI")


class CLIActions(Protocol[T]):
    params: T
    action: ActionField


@dataclass
class CLI:
    _TYRO_CLI_CONFIG = (
        tyro.conf.CascadeSubcommandArgs,
        tyro.conf.OmitSubcommandPrefixes,
        tyro.conf.SuppressFixed,
    )

    @classmethod
    def cli_config(cls, base_cls: type[T] | None = None) -> type[CLIConfig[T]]:
        return cast(
            "type[CLIConfig]",
            make_dataclass(
                cls.__name__,
                [
                    (
                        "params",
                        Annotated[cls, tyro.conf.arg(name="")],  # ty: ignore[invalid-type-form]
                        field(default=MISSING),
                    ),
                    (
                        "action",
                        ActionField,
                        field(default_factory=RunAction, kw_only=True),
                    ),
                ],
                bases=(base_cls or CLI,),
            ),
        )

    @overload
    @classmethod
    def instance_from_cli(
        cls,
        prog: str | None = None,
        *args: Any,
        return_unknown_args: Literal[False] = ...,
        **kwargs: Any,
    ) -> Self: ...

    @overload
    @classmethod
    def instance_from_cli(
        cls,
        prog: str | None = None,
        *args: Any,
        return_unknown_args: Literal[True],
        **kwargs: Any,
    ) -> tuple[Self, Sequence[str]]: ...

    @classmethod
    def instance_from_cli(
        cls, prog: str | None = None, *args: Any, **kwargs: Any
    ) -> Self | tuple[Self, Sequence[str]]:
        return tyro.cli(
            cls, *args, prog=prog, config=cls._TYRO_CLI_CONFIG, **kwargs
        )


@dataclass
class CLIConfig(CLIActions, CLI, Generic[T]):
    pass
