from __future__ import annotations

import sys
from dataclasses import dataclass, field, make_dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Generic,
    Literal,
    TypeVar,
    cast,
    overload,
)

import tyro

from bdbox.actions.field import ActionField  # noqa: TC001
from bdbox.actions.run import RunAction
from bdbox.console import console

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Sequence


T = TypeVar("T", bound="CLI")

TYRO_CLI_CONFIG = (
    tyro.conf.CascadeSubcommandArgs,
    tyro.conf.OmitSubcommandPrefixes,
    tyro.conf.SuppressFixed,
)


@dataclass
class CLIOptions:
    verbose: Annotated[
        tyro.conf.UseCounterAction[int],
        tyro.conf.arg(
            aliases=["-v"],
            help=("Increase logging verbosity."),
        ),
        tyro.conf.FlagCreatePairsOff,
    ] = field(default=0, kw_only=True)

    def configure(self) -> None:
        console.configure(verbose=self.verbose)

    @classmethod
    def configure_from_cli(
        cls, prog: str | None = None, *args: Any, **kwargs: Any
    ) -> Self:
        instance, _ = tyro.cli(
            cls,
            *args,
            prog=prog,
            return_unknown_args=True,
            add_help=False,
            config=TYRO_CLI_CONFIG,
            **kwargs,
        )
        instance.configure()
        return instance

    def to_args(self) -> Sequence[str]:
        if self.verbose:
            return ["-" + ("v" * self.verbose)]
        return []


@dataclass
class CLI:
    package: ClassVar[str] = (__package__ or "bdbox").split(".", 1)[0]

    @classmethod
    def prog(cls) -> str:
        if (argv0 := Path(sys.argv[0])).stem == "__main__":
            return cls.package
        return argv0.name

    @classmethod
    def cli_config(cls) -> type[CLIConfig[T]]:
        return cast(
            "type[CLIConfig]",
            make_dataclass(cls.__name__, [], bases=(CLIConfig[cls],)),  # ty: ignore[invalid-type-form]
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
        prog = prog or cls.prog()
        result = tyro.cli(
            cls, *args, prog=prog, config=TYRO_CLI_CONFIG, **kwargs
        )
        if isinstance(result, CLIOptions):
            result.configure()
        return result


@dataclass
class CLIConfig(CLI, CLIOptions, Generic[T]):
    params: Annotated[T, tyro.conf.arg(name="")]
    action: ActionField = field(default_factory=RunAction, kw_only=True)
