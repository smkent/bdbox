from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import patch

from bdbox.actions.run import RunAction
from bdbox.errors import Error

from .shims import AtExit, MainModule
from .utils import ModelLocator, PatchModule, reset_bdbox

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bdbox.actions.action import Action


@dataclass
class ModelRunner(ModelLocator):
    action: Action | None = None

    @dataclass
    class ExitError(Exception):
        code: int | str

    def __call__(self, action: Action | None = None) -> None:
        if not self.model_filename:
            raise Error("Model not found in arguments")
        reset_bdbox()
        main_module = MainModule(
            filename=self.model_filename, module_name=self.model_module
        )
        with (
            PatchModule("__main__", main_module, auto=False) as mock_main,
            patch.object(sys, "argv", [self.model_filename, *self.argv]),
            self.exit_mock(),
            AtExit.mock() as atexit_mock,
        ):
            main_module.run_main_shim()
            mock_main.start()
            if not atexit_mock.hooks:
                (action or self.action or RunAction())()

    @classmethod
    @contextmanager
    def exit_mock(cls) -> Iterator[None]:
        def stub(code: str | int) -> None:
            raise cls.ExitError(code)

        with patch.object(sys, "exit", stub), patch.object(os, "_exit", stub):
            try:
                yield
            except cls.ExitError as e:
                raise SystemExit(e.code) from e
