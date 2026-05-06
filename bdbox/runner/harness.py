from __future__ import annotations

import ast
import operator
import sys
from contextlib import suppress
from dataclasses import dataclass, field, make_dataclass
from functools import cached_property, reduce
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, cast, get_args
from unittest.mock import MagicMock, patch

import tyro

from bdbox.actions.action import Action, ModelAction
from bdbox.actions.field import ActionField
from bdbox.cli import CLI
from bdbox.errors import Error
from bdbox.parameters.state import run_state

from .locator import ModelLocator
from .runner import ModelRunner
from .shims import MainModule
from .utils import Build123dStub, PatchModule
from .watcher import ModelWatcher

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bdbox.parameters.parameters import Params


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
    clean_modules: ClassVar[bool] = True
    package: ClassVar[str] = (__package__ or "bdbox").split(".", 1)[0]
    rerender_event: Event = field(
        default_factory=Event, init=False, repr=False
    )

    @dataclass
    class HarnessCLI(CLI):
        action: HarnessAction

    def __post_init__(
        self, model_argv: Sequence[Path | str] | Path | str
    ) -> None:
        Action.mode = Action.Mode.HARNESS
        super().__post_init__(model_argv or sys.argv[1:].copy())

    def __call__(self) -> None:
        cli_cls = (
            ((self.model_params_cls or CLI).cli_config())
            if self.maybe_model
            else self.HarnessCLI
        )
        main_module = MainModule()
        main_module.__dict__.update(run_state.module_dict)
        with PatchModule("__main__", main_module, auto=True):
            cli_result = cli_cls.instance_from_cli(
                prog=self.prog, args=self.argv
            )
        hook_result = cli_result.action.before_harness(self)
        if not self.maybe_model:
            return
        if hook_result and hook_result.runs:
            for argv, action in hook_result.runs:
                ModelRunner(argv, action)()
            return
        runner = ModelRunner([self.model, *self.argv], cli_result.action)
        if cli_result.action.watch:
            ModelWatcher(runner=runner, change_event=self.rerender_event).run()
            return
        runner()

    @cached_property
    def params_argv(self) -> Sequence[str]:
        _, params_argv = (
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
        return params_argv

    @cached_property
    def maybe_model(self) -> Path | str | None:
        with suppress(Error):
            return self.model

    @cached_property
    def model(self) -> Path | str:
        if self.model_module and self.model_class_name:
            return f"{self.model_module}:{self.model_class_name}"
        if result := (self.model_module or self.model_path):
            return result
        raise Error("No model found")

    @cached_property
    def prog(self) -> str:
        if (argv0 := Path(sys.argv[0])).stem == "__main__":
            return self.package
        return argv0.name

    @cached_property
    def imports_detected(self) -> bool:
        """Return True if the model file imports bdbox."""

        def _checkname(name: str) -> bool:
            return name == self.package or name.startswith(f"{self.package}.")

        if self.model_module:
            return True
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
        if not self.model:
            return None
        with (
            patch.dict(
                sys.modules,
                {"build123d": Build123dStub(), "ocp_vscode": MagicMock()},
            ),
            patch.object(
                CLI, "instance_from_cli", MagicMock(side_effect=SystemExit)
            ),
            self.module_cleanup(),
            suppress(SystemExit),
        ):
            ModelRunner([self.model, "--help"])()
        if not (model_class := run_state.get_model()):
            return None
        if getattr(model_class, "__module__", None) != "__main__":
            model_class.__module__ = "__main__"
        return model_class
