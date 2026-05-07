from __future__ import annotations

import runpy
import sys
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

from bdbox.actions.run import RunAction
from bdbox.errors import InternalError, RunError
from bdbox.parameters.state import run_state

from .locator import ModelLocator
from .shims import AtExit, MainModule
from .utils import PatchModule, exit_mock, reset_bdbox

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bdbox.actions.action import Action


@dataclass
class ModelRunner(ModelLocator):
    action: Action | None = None
    preserve_exceptions: bool = False

    def __call__(self, action: Action | None = None) -> None:
        if not self.model_filename:
            raise InternalError("Model not found in arguments")
        reset_bdbox()
        run_state.action = action or self.action or RunAction()
        main_module = MainModule(
            filename=self.model_filename, module_name=self.model_module
        )
        try:
            with (
                action.on_model_render() if action else nullcontext(),
                PatchModule("__main__", main_module, auto=False) as mock_main,
                patch.object(sys, "argv", [self.model_filename, *self.argv]),
                exit_mock(),
                AtExit.mock() as atexit_mock,
                self._ensure_stack_closed(),
            ):
                main_module.__dict__.update(self._run_model())
                mock_main.start()
                if not atexit_mock.hooks:
                    run_state.act_once()
        except (SystemExit, Exception) as e:
            if self.preserve_exceptions:
                raise
            raise RunError(e) from e

    def _run_model(self) -> dict[str, Any]:
        if self.model_module:
            run_state.module_name = self.model_module
            run_state.class_name = self.model_class_name
            results = runpy.run_module(
                self.model_module, run_name="__main__", alter_sys=True
            )
        elif self.model_filename:
            results = runpy.run_path(self.model_filename, run_name="__main__")
        else:
            raise InternalError("One of filename or module_name are required")
        return results

    @contextmanager
    def _ensure_stack_closed(self) -> Iterator[None]:
        try:
            yield
        finally:
            run_state.close_stack()
