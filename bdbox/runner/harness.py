from __future__ import annotations

import operator
import os
import sys
from contextlib import suppress
from dataclasses import dataclass, field, make_dataclass
from functools import cached_property, reduce
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, cast, get_args
from unittest.mock import MagicMock, patch

import tyro

from bdbox.actions.action import ModelAction
from bdbox.actions.field import ActionField
from bdbox.cli import CLI, CLIOptions
from bdbox.dispatch import Event, dispatch
from bdbox.errors import InternalError, RunError
from bdbox.runner.state import run_state

from .env import EnvLocator
from .locator import ModelLocator
from .runner import ModelRunner
from .shims import MainModule
from .utils import Build123dStub, PatchModule
from .watcher import ModelWatcher

if TYPE_CHECKING:
    from collections.abc import Sequence

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
class ModelHarness(ModelLocator):
    env_search: ClassVar[bool] = True
    clean_modules: ClassVar[bool] = True
    package: ClassVar[str] = (__package__ or "bdbox").split(".", 1)[0]
    rerender_event: Event = field(
        default_factory=lambda: Event(name="rerender_event"),
        init=False,
        repr=False,
    )

    @dataclass
    class HarnessCLI(CLI, CLIOptions):
        action: HarnessAction

    def __post_init__(
        self, model_argv: Sequence[Path | str] | Path | str
    ) -> None:
        run_state.mode = run_state.Mode.HARNESS
        argv = self._setup_argv(model_argv or sys.argv[1:])
        CLIOptions.configure_from_cli(args=argv)
        super().__post_init__(argv)
        if len(sys.argv) == 1:
            self.argv.append("--help")

    def __call__(self) -> None:
        cli_cls = (
            ((self.model_params_cls or CLI).cli_config())
            if self.maybe_model
            else self.HarnessCLI
        )
        main_module = MainModule()
        main_module.__dict__.update(run_state.model_state.module_dict)
        with PatchModule("__main__", main_module, auto=True):
            cli_result = cli_cls.instance_from_cli(
                prog=self.prog, args=self.argv
            )
        hook_result = cli_result.action.before_harness(self)
        if not self.maybe_model:
            return
        if hook_result and hook_result.runs:
            for argv, action in hook_result.runs:
                ModelRunner(
                    argv, action, preserve_exceptions=True
                ).run_or_exit()
            return
        runner = ModelRunner([self.model_arg, *self.argv], cli_result.action)
        if cli_result.action.watch:
            ModelWatcher(runner=runner, change_event=self.rerender_event).run()
            dispatch.exit.set()
            dispatch.exit_join()
            return
        runner.preserve_exceptions = True
        runner.run_or_exit()
        dispatch.exit.set()
        dispatch.exit_join()

    @cached_property
    def params_argv(self) -> Sequence[str]:
        inst, params_argv = (
            cast(
                "CLI",
                make_dataclass(
                    CLI.__name__,
                    [("preset", "str | None", None)],
                    bases=(CLI,),
                ),
            )
            .cli_config()
            .instance_from_cli(
                prog=self.prog,
                args=self.argv,
                return_unknown_args=True,
                add_help=False,
            )
        )
        return [*params_argv, *inst.to_args()]

    @cached_property
    def maybe_model(self) -> Path | str | None:
        with suppress(InternalError):
            return self.model_arg

    @cached_property
    def model_arg(self) -> Path | str:
        if self.model.module_name and self.model.class_name:
            return f"{self.model.module_name}:{self.model.class_name}"
        if result := (self.model.module_name or self.model.path):
            return result
        raise InternalError("No model found")

    @cached_property
    def prog(self) -> str:
        if (argv0 := Path(sys.argv[0])).stem == "__main__":
            return self.package
        return argv0.name

    def get_model(self) -> type[Params] | None:
        with (
            patch.dict(
                sys.modules,
                {"build123d": Build123dStub(), "ocp_vscode": MagicMock()},
            ),
            patch.object(
                CLI, "instance_from_cli", MagicMock(side_effect=SystemExit)
            ),
            self.module_cleanup(),
            suppress(RunError, InternalError),
        ):
            ModelRunner([self.model_arg, "--help"], discovery_mode=True)()
        return run_state.model_state.get_model()

    @cached_property
    def model_params_cls(self) -> type[Params] | None:
        """Discover model parameters by running the model in discovery mode.

        Returns a list of (name, annotation, field) tuples for user-defined
        parameters, or None if no bdbox Params/Model class was found.
        """
        if not self.maybe_model:
            return None
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
                    del self.model_arg
                    if model_class := self.get_model():
                        return model_class
                    self.model.module_name = None
                    del self.model_arg
            return None
        if getattr(model_class, "__module__", None) != "__main__":
            model_class.__module__ = "__main__"
        return model_class
