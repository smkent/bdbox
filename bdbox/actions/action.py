"""bdbox action base class."""

from __future__ import annotations

import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bdbox.console import console, log
from bdbox.errors import RunError, UsageError
from bdbox.runner.runner import ModelRunner
from bdbox.runner.state import run_state

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bdbox.model.info import ModelInfo
    from bdbox.timer import Timer


@dataclass
class Action:
    """Base class for bdbox actions."""

    def __call__(self) -> None:
        """Execute this action with the given geometry."""
        raise NotImplementedError

    def on_harness(self, model: ModelInfo) -> None:
        """Executed when run from the harness."""
        raise NotImplementedError

    @contextmanager
    def on_model_render(self) -> Iterator[Timer]:
        """Executed around model run."""
        with (
            run_state.model_state.set_running() as timer,
            console.log_stdout_stderr(),
            console.activity_indicator(timer),
        ):
            try:
                yield timer
            except (Exception, SystemExit) as e:
                log.exception("Run failed (%s)", timer.elapsed_str)
                raise RunError(e) from e
            else:
                log.info("Run complete (%s)", timer.elapsed_str)


@dataclass
class ModelAction(Action):
    def on_harness(self, model: ModelInfo) -> None:
        if not (model_arg := model.arg):
            raise UsageError("No model specified")
        ModelRunner(
            [model_arg, *model.argv],
            action=self,
            preserve_exceptions=True,
        ).run_or_exit()

    def _ensure_runner(self) -> None:
        if run_state.mode != run_state.Mode.HARNESS:
            try:
                cmd = [sys.executable, "-m", "bdbox", *sys.argv]
                log.debug(f"Exec: {' '.join(cmd)}")
                returncode = subprocess.run(cmd).returncode  # noqa: S603, PLW1510
            except KeyboardInterrupt:
                sys.exit(130)
            except Exception:  # noqa: BLE001
                sys.exit(2)
            sys.exit(returncode)


@dataclass
class CommandAction(Action):
    def on_harness(
        self,
        model: ModelInfo,  # noqa: ARG002
    ) -> None:
        self()

    @contextmanager
    def on_model_render(self) -> Iterator[None]:
        self()
        yield

    def __call__(self) -> None:
        sys.exit(0)
