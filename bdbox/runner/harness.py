from __future__ import annotations

import ast
import sys
from contextlib import suppress
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, ClassVar, cast
from unittest.mock import MagicMock, patch

import tyro

from bdbox import Params
from bdbox.actions.field import ActionField  # noqa: TC001
from bdbox.actions.run import RunAction
from bdbox.cli import CLI

from .runner import ModelRunner

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class ModelHarness(ModelRunner):
    filename: str | Path | None = field(default=None, init=False)
    package: ClassVar[str] = (__package__ or "bdbox").split(".", 1)[0]
    argv_run: Sequence[str] = field(default_factory=tuple, init=False)

    class MultipleModelsError(Exception):
        pass

    @dataclass
    class HarnessCLI(CLI):
        model: Annotated[
            str,
            tyro.conf.Positional,
            tyro.conf.arg(metavar="model-path", help="Model file to run."),
        ]
        action: ActionField = field(default_factory=RunAction, kw_only=True)

    def __post_init__(self) -> None:
        self.argv_run = (
            list(self.argv[1:]) if self.argv else sys.argv[1:].copy()
        )
        if pstr := self._model_path_from_argv():
            self.filename = pstr
            # Move model filename to the front of the arguments list
            self.argv_run.insert(
                0, self.argv_run.pop(self.argv_run.index(pstr))
            )

    @cached_property
    def prog(self) -> str:
        if (argv0 := Path(sys.argv[0])).stem == "__main__":
            return self.package
        return argv0.name

    def run_model(self) -> None:
        actionable, _ = self.cli_class.instance_from_cli(
            prog=self.prog, args=self.argv_run, return_unknown_args=True
        )
        model_argv = self.argv_run[1:]
        actionable.action.before_harness_model(actionable.model, model_argv)
        ModelRunner(actionable.model, model_argv, actionable.action)()

    def _model_path_from_argv(self) -> str | None:
        for arg in self.argv_run:
            if not arg.startswith("-") and Path(arg).suffix == ".py":
                return arg
        return None

    @cached_property
    def cli_class(self) -> type[ModelHarness.HarnessCLI]:
        cli_class: type[self.HarnessCLI] = self.HarnessCLI
        if model_cls := self._model_params_cls:
            return cast(
                "type[self.HarnessCLI]", model_cls.cli_config(self.HarnessCLI)
            )
        return cli_class

    @cached_property
    def _imports_detected(self) -> bool:
        """Return True if the model file imports bdbox."""

        def _checkname(name: str) -> bool:
            return name == self.package or name.startswith(f"{self.package}.")

        if not (self.filename and self.model_path):
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
    def _model_params_cls(self) -> type[Params] | None:
        """Discover model parameters by running the model in discovery mode.

        Returns a list of (name, annotation, field) tuples for user-defined
        parameters, or None if no bdbox Params/Model class was found.
        """
        if not (self.filename and self.model_path and self._imports_detected):
            return None
        with (
            patch.dict(sys.modules, {"build123d": MagicMock()}),
            patch.object(
                CLI, "instance_from_cli", MagicMock(side_effect=SystemExit)
            ),
            suppress(SystemExit, ModelRunner.ExitError),
        ):
            ModelRunner(self.model_path, ["--help"])()
        if not (subclasses := Params._main_info.model_subclasses):  # noqa: SLF001
            return None
        if len(subclasses) > 1:
            raise self.MultipleModelsError(subclasses)
        return subclasses[0]
