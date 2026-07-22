from __future__ import annotations

import sys
from dataclasses import dataclass, field, make_dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Generic,
    TypeVar,
    cast,
    get_origin,
    overload,
)

import tyro

from bdbox.actions.action import CommandAction
from bdbox.actions.field import ActionField  # noqa: TC001
from bdbox.actions.run import RunAction
from bdbox.console import console

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Sequence


T = TypeVar("T")

TYRO_CLI_CONFIG = (
    tyro.conf.CascadeSubcommandArgs,
    tyro.conf.OmitSubcommandPrefixes,
    tyro.conf.SuppressFixed,
)


@dataclass
class CLIOptions:
    verbose: Annotated[
        tyro.conf.UseCounterAction[int],
        tyro.conf.arg(aliases=["-v"], help="Increase logging verbosity."),
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
class CLIAction(CLIOptions, Generic[T]):
    action: ActionField = field(default_factory=RunAction, kw_only=True)
    params: tyro.conf.Suppress[T | None] = field(default_factory=lambda: None)


@dataclass
class CLIConfig(CLIAction[T]):
    params: Annotated[T, tyro.conf.arg(name="")]


@dataclass
class CLIParser:
    package: str = (__package__ or "bdbox").split(".", 1)[0]

    @property
    def prog(self) -> str:
        if (argv0 := Path(sys.argv[0])).stem == "__main__":
            return self.package
        return argv0.name

    def cli_config(self, cls: type[T]) -> type[CLIConfig[T]]:
        return cast(
            "type[CLIConfig]",
            make_dataclass("CLIConfig", [], bases=(CLIConfig[cls],)),  # ty: ignore[invalid-type-form]
        )

    @overload
    def parse(self, cls: None, **kwargs: Any) -> CLIAction[None]: ...

    @overload
    def parse(
        self, cls: type[CLIAction[T]], **kwargs: Any
    ) -> CLIAction[T]: ...

    @overload
    def parse(
        self, cls: type[T], **kwargs: Any
    ) -> CLIConfig[T] | CLIAction[None]: ...

    def parse(
        self,
        cls: type[T] | None,
        *,
        args: Sequence[Any] | None = None,
        prog: str | None = None,
        **kwargs: Any,
    ) -> CLIAction[None] | CLIConfig[T]:
        prog = prog or self.prog
        preparse_action = True
        for arg in args or []:
            if arg in {"-h", "--help"}:
                preparse_action = False
        if preparse_action:
            action_result, _ = self.preparse(
                cls=CLIAction[None], args=args, prog=prog, **kwargs
            )
            if isinstance(action_result.action, CommandAction):
                return action_result

        cli_cls = self._cli(cls)
        result = tyro.cli(
            cli_cls,
            args=args,
            prog=prog,
            config=TYRO_CLI_CONFIG,
            return_unknown_args=False,
            **kwargs,
        )
        if isinstance(result, CLIOptions):
            result.configure()
        return result

    @overload
    def preparse(
        self, cls: None, **kwargs: Any
    ) -> tuple[CLIAction[None], Sequence[str]]: ...

    @overload
    def preparse(
        self, cls: type[CLIAction[T]], **kwargs: Any
    ) -> tuple[CLIAction[T], Sequence[str]]: ...

    @overload
    def preparse(
        self, cls: type[T], **kwargs: Any
    ) -> tuple[CLIConfig[T], Sequence[str]]: ...

    def preparse(
        self,
        cls: type[T] | None,
        *,
        args: Sequence[Any] | None = None,
        prog: str | None = None,
        **kwargs: Any,
    ) -> tuple[CLIAction[None] | CLIConfig[T], Sequence[str]]:
        prog = prog or self.prog
        cli_cls = self._cli(cls)
        result, extra_args = tyro.cli(
            cli_cls,
            args=args,
            prog=prog,
            return_unknown_args=True,
            add_help=False,
            config=TYRO_CLI_CONFIG,
            **kwargs,
        )
        return result, extra_args

    @overload
    def _cli(self, cls: None) -> type[CLIAction[None]]: ...

    @overload
    def _cli(self, cls: type[CLIAction[T]]) -> type[CLIAction[T]]: ...

    @overload
    def _cli(self, cls: type[T]) -> type[CLIConfig[T]]: ...

    def _cli(
        self, cls: type[T] | None
    ) -> type[T | CLIAction[None] | CLIConfig[T]]:
        if not cls:
            return CLIAction[None]
        if issubclass(get_origin(cls) or cls, CLIAction):
            return cls
        return self.cli_config(cls)


cli_parser = CLIParser()
