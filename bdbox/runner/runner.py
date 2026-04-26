from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from dataclasses import InitVar, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from bdbox.actions.run import RunAction
from bdbox.errors import Error

from .shims import AtExit, MainModule
from .utils import PatchModule, reset_bdbox

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from bdbox.actions.action import Action


@dataclass
class ModelRunner:
    model_argv: InitVar[Sequence[Path | str] | Path | str]
    model_path: Path = field(init=False)
    model_filename: str = field(init=False)
    argv: list[str] = field(default_factory=list, init=False)
    action: Action | None = None

    @dataclass
    class ExitError(Exception):
        code: int | str

    def __post_init__(
        self, model_argv: Sequence[Path | str] | Path | str
    ) -> None:
        self.argv = (
            [str(model_argv)]
            if isinstance(model_argv, (Path, str))
            else [str(v) for v in model_argv]
        )
        model = self.model_path_from_argv()
        self.model_path = Path(model)
        self.model_filename = str(model)

    def __call__(self, action: Action | None = None) -> None:
        reset_bdbox()
        main_module = self.main_module()
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

    def main_module(self) -> MainModule:
        return MainModule(self.model_filename)

    def model_path_from_argv(self) -> str:
        for arg in self.argv:
            if not arg.startswith("-") and Path(arg).suffix == ".py":
                self.argv.pop(self.argv.index(arg))
                return arg
        raise Error("Model not found in arguments")

    @classmethod
    @contextmanager
    def exit_mock(cls) -> Iterator[MagicMock]:
        def stub(code: str | int) -> None:
            raise cls.ExitError(code)

        mock_exit = MagicMock(name="exit", side_effect=stub)
        with (
            patch.object(sys, "exit", mock_exit),
            patch.object(os, "_exit", mock_exit),
        ):
            try:
                yield mock_exit
            except cls.ExitError as e:
                raise SystemExit(e.code) from e
