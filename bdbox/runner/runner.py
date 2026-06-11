from __future__ import annotations

import runpy
import sys
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

from bdbox.errors import InternalError, RunError
from bdbox.runner.state import run_state

from .locator import ModelLocator
from .shims import AtExit, MainModule
from .utils import PatchModule, exit_mock

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bdbox.actions.action import Action


@dataclass
class ModelRunner(ModelLocator):
    action: Action | None = None
    preserve_exceptions: bool = field(default=False, kw_only=True)
    discovery_mode: bool = field(default=False, kw_only=True)

    def __call__(self) -> None:
        if not self.model.filename:
            raise InternalError("Model not found in arguments")
        run_state.reset()
        run_state.mode = run_state.Mode.HARNESS
        if self.action:
            run_state.action_state.action = self.action
        main_module = MainModule(
            filename=self.model.filename, module_name=self.model.module_name
        )
        try:
            with (
                self.action_on_model_render(),
                PatchModule("__main__", main_module, auto=False) as mock_main,
                patch.object(sys, "argv", [self.model.filename, *self.argv]),
                exit_mock(),
                AtExit.mock() as atexit_mock,
            ):
                main_module.__dict__.update(self._run_model())
                mock_main.start()
                if not atexit_mock.hooks:
                    run_state.action_state.act_once()
        except (SystemExit, Exception) as e:
            if self.preserve_exceptions:
                raise
            raise RunError(e) from e

    def run_or_exit(self) -> None:
        try:
            self()
        except RunError:
            sys.exit(1)

    def _run_model(self) -> dict[str, Any]:
        run_state.model_state.model = deepcopy(self.model)
        if self.model.module_name:
            results = runpy.run_module(
                self.model.module_name, run_name="__main__", alter_sys=True
            )
        elif self.model.filename:
            results = runpy.run_path(self.model.filename, run_name="__main__")
        else:
            raise InternalError("One of filename or module_name are required")
        return results

    @contextmanager
    def action_on_model_render(self) -> Iterator[None]:
        if self.action and not self.discovery_mode:
            with run_state.action_state.on_model_render():
                yield
        else:
            yield
