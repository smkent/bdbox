from __future__ import annotations

import operator
import os
import sys
from contextlib import suppress
from dataclasses import dataclass, make_dataclass
from functools import cached_property, reduce
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, get_args
from unittest.mock import MagicMock, patch

import tyro

from bdbox.actions.action import ModelAction
from bdbox.actions.field import ActionField
from bdbox.cli import CLIAction, CLIOptions, cli_parser
from bdbox.dispatch import dispatch
from bdbox.errors import InternalError, RunError
from bdbox.runner.state import run_state

from .env import EnvLocator
from .locator import ModelLocator
from .runner import ModelRunner
from .shims import MainModule
from .utils import Build123dStub, PatchModule

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from bdbox.model.parameters import Params


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
            base_cls.__name__,
            [],
            bases=(base_cls, cls.ModelArgument),
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


@dataclass
class ModelHarness(ModelLocator):
    env_search: ClassVar[bool] = True

    @cached_property
    def harness_cli(self) -> type[CLIAction[None]]:
        @dataclass
        class HarnessCLI(CLIAction[None]):
            HarnessAction = HarnessCLIFactory.make()

            action: HarnessAction

        return HarnessCLI

    def __post_init__(
        self, model_argv: Sequence[Path | str] | Path | str
    ) -> None:
        run_state.mode = run_state.Mode.HARNESS
        argv = self._setup_argv(model_argv or sys.argv[1:])
        CLIOptions.configure_from_cli(args=argv)
        super().__post_init__(argv)
        if not argv:
            self.model.argv.append("--help")

    def __call__(self) -> None:
        self.model.params_class = self.model_params_cls
        cli_cls = (
            self.model.params_class if self.model.arg else self.harness_cli
        )
        main_module = MainModule()
        main_module.__dict__.update(run_state.model_state.module_dict)
        with PatchModule("__main__", main_module, auto=True):
            cli_result = cli_parser.parse(cli_cls, args=self.model.argv)
        cli_result.action.on_harness(self.model)
        dispatch.exit.set()
        dispatch.exit_join()

    def get_model(self) -> type[Params] | None:
        if model_arg := self.model.arg:
            with (
                PatchModule("build123d", Build123dStub(), recursive=True),
                PatchModule("ocp_vscode"),
                patch.object(
                    cli_parser, "parse", MagicMock(side_effect=SystemExit)
                ),
                self.module_cleanup(),
                suppress(RunError, InternalError),
            ):
                ModelRunner([model_arg, "--help"], discovery_mode=True)()
        return run_state.model_state.get_model()

    @cached_property
    def model_params_cls(self) -> type[Params] | None:
        """Discover model parameters by running the model in discovery mode.

        Returns a list of (name, annotation, field) tuples for user-defined
        parameters, or None if no bdbox Params/Model class was found.
        """
        if not (model_class := self.get_model()):
            if not self.model.module_name and self.model.path:
                with suppress(ValueError):
                    env = EnvLocator(self.model.path).project_root()
                    relative = self.model.path.relative_to(env)
                    os.chdir(env)
                    mod_name = (
                        str(relative).removesuffix(".py").replace(os.sep, ".")
                    )
                    self.model.module_name = mod_name
                    if model_class := self.get_model():
                        return model_class
                    self.model.module_name = None
            return None
        if getattr(model_class, "__module__", None) != "__main__":
            model_class.__module__ = "__main__"
        return model_class
