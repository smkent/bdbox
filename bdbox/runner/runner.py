from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

from bdbox import Model, Params
from bdbox.actions.action import Action
from bdbox.actions.run import RunAction
from bdbox.geometry import reset_geometry

from .shims import AtExit, MainModule
from .utils import PatchModule

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


@dataclass
class ModelRunner:
    filename: str | Path
    argv: Sequence[str] = field(default_factory=tuple)
    action: Action | None = None

    class ExitError(Exception):
        pass

    @cached_property
    def model_filename(self) -> str:
        return str(self.filename)

    @cached_property
    def model_path(self) -> Path:
        return Path(self.filename).resolve()

    @classmethod
    def create_and_run_stub(
        cls,
        filename: str | Path,
        argv: Sequence[str] = (),
        action: Action | None = None,
        **run_kwargs: Any,
    ) -> None:
        return cls(filename, argv, action)(**run_kwargs)

    def __post_init__(self) -> None:
        self.main_module = MainModule(self.model_filename)

    def __call__(self, action: Action | None = None) -> None:
        self._reset_model_main_stub()
        with (
            patch.object(Action, "mode", Action.Mode.RUNNER),
            PatchModule("__main__", self.main_module, auto=False) as mock_main,
            patch.object(sys, "argv", [self.model_filename, *self.argv]),
            self._exit_mock(),
            AtExit.mock() as atexit_mock,
        ):
            self.main_module.run_main_shim()
            mock_main.start()
            if not atexit_mock.hooks:
                (action or self.action or RunAction())()

    @classmethod
    @contextmanager
    def _exit_mock(cls) -> Iterator[MagicMock]:
        mock_exit = MagicMock(name="exit", side_effect=cls.ExitError())
        with (
            patch.object(sys, "exit", mock_exit),
            patch.object(os, "_exit", mock_exit),
        ):
            yield mock_exit
        mock_exit.assert_not_called()

    @staticmethod
    def _reset_model_main_stub() -> Any:
        """Reset all bdbox module-level state for runners or tests."""
        reset_geometry()
        for params_class in [Params, Model]:
            params_class._main_info.__init__()  # noqa: SLF001
