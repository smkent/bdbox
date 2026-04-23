from __future__ import annotations

import ast
import operator
import sys
from contextlib import suppress
from dataclasses import InitVar, dataclass, field, make_dataclass
from functools import cached_property, reduce
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, get_args
from unittest.mock import MagicMock, patch

import tyro

from bdbox import Params
from bdbox.actions.action import Action, ModelAction
from bdbox.actions.field import ActionField
from bdbox.cli import CLI

from .runner import ModelRunner
from .watcher import ModelWatcher

if TYPE_CHECKING:
    from collections.abc import Sequence


class HarnessCLIFactory:
    @dataclass
    class ModelArgument:
        model: Annotated[
            str,
            tyro.conf.Positional,
            tyro.conf.arg(metavar="model", help="Model file to run."),
        ]

    @classmethod
    def append_model_argument(cls, action_cls: type) -> Annotated[Any, ...]:
        base_cls, *original_annotations = get_args(action_cls)
        if not (type(base_cls) is type and issubclass(base_cls, ModelAction)):
            return action_cls
        new_cls = make_dataclass(
            base_cls.__name__, [], bases=(base_cls, cls.ModelArgument)
        )
        return Annotated[(new_cls, *original_annotations)]  # ty: ignore[invalid-type-form]

    @classmethod
    def make(cls) -> Annotated[Any, ...]:
        return reduce(
            operator.or_,
            tuple(
                cls.append_model_argument(sub) for sub in get_args(ActionField)
            ),
        )


HarnessAction = HarnessCLIFactory.make()


@dataclass
class ModelHarness:
    package: ClassVar[str] = (__package__ or "bdbox").split(".", 1)[0]
    model_argv: InitVar[Sequence[Path | str] | Path | str] = ()
    model_path: Path | None = field(default=None, init=False)
    model_filename: str | Path | None = field(default=None, init=False)
    argv: list[str] = field(default_factory=list, init=False)

    class MultipleModelsError(Exception):
        pass

    @dataclass
    class HarnessCLI(CLI):
        action: HarnessAction

    def __post_init__(
        self, model_argv: Sequence[Path | str] | Path | str
    ) -> None:
        Action.mode = Action.Mode.HARNESS
        self.argv = (
            [str(model_argv)]
            if isinstance(model_argv, (Path, str))
            else [str(v) for v in (model_argv or sys.argv[1:].copy())]
        )
        if model := self.model_path_from_argv():
            self.model_path = Path(model)
            self.model_filename = str(model)

    def __call__(self) -> None:
        if not self.model_filename or not self.model_path:
            cli_result = self.HarnessCLI.instance_from_cli(
                prog=self.prog, args=self.argv, harness_hook=True
            )
            return

        cli_result = (
            (self.model_params_cls or CLI)
            .cli_config()
            .instance_from_cli(
                prog=self.prog,
                args=self.argv,
                harness_hook=True,
                model_hook=False,
            )
        )
        runner = ModelRunner([self.model_path, *self.argv], cli_result.action)
        if cli_result.action.watch:
            ModelWatcher(runner).run()
            return
        runner()

    @cached_property
    def prog(self) -> str:
        if (argv0 := Path(sys.argv[0])).stem == "__main__":
            return self.package
        return argv0.name

    def model_path_from_argv(self) -> str | None:
        for arg in self.argv:
            if not arg.startswith("-") and Path(arg).suffix == ".py":
                self.argv.pop(self.argv.index(arg))
                return arg
        return None

    @cached_property
    def imports_detected(self) -> bool:
        """Return True if the model file imports bdbox."""

        def _checkname(name: str) -> bool:
            return name == self.package or name.startswith(f"{self.package}.")

        if not self.model_path:
            return False
        with suppress(OSError, SyntaxError):
            tree = ast.parse(self.model_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(_checkname(alias.name) for alias in node.names):
                        return True
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and _checkname(node.module)
                ):
                    return True
        return False

    @cached_property
    def model_params_cls(self) -> type[Params] | None:
        """Discover model parameters by running the model in discovery mode.

        Returns a list of (name, annotation, field) tuples for user-defined
        parameters, or None if no bdbox Params/Model class was found.
        """
        if not (self.model_path and self.imports_detected):
            return None
        with (
            patch.dict(
                sys.modules,
                {"build123d": MagicMock(), "ocp_vscode": MagicMock()},
            ),
            patch.object(
                CLI, "instance_from_cli", MagicMock(side_effect=SystemExit)
            ),
            suppress(SystemExit),
        ):
            ModelRunner([self.model_path, "--help"])()
        if not (subclasses := Params._main_info.model_subclasses):  # noqa: SLF001
            return None
        if len(subclasses) > 1:
            raise self.MultipleModelsError(subclasses)
        return subclasses[0]
