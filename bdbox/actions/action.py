"""bdbox action base class."""

from __future__ import annotations

import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

import tyro  # noqa: TC002

from bdbox.console import console, log
from bdbox.errors import RunError
from bdbox.runner.state import run_state

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from bdbox.dispatch import Event
    from bdbox.model.parameters import Params
    from bdbox.timer import Timer


@dataclass
class Action:
    """Base class for bdbox actions."""

    watch: tyro.conf.Fixed[bool] = field(default=False, kw_only=True)

    class ModelHarnessProtocol(Protocol):
        model_arg: Path | str
        params_argv: Sequence[str]
        model_params_cls: type[Params] | None
        rerender_event: Event

    @dataclass
    class HarnessResult:
        runs: Sequence[tuple[Sequence[str | Path], Action]]

    BeforeHarnessResult = HarnessResult | None

    def __call__(self) -> None:
        """Execute this action with the given geometry."""
        raise NotImplementedError

    def before_harness(
        self, args: Action.ModelHarnessProtocol
    ) -> Action.BeforeHarnessResult:
        """Executed prior to running the harness."""

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
    def before_harness(
        self,
        args: Action.ModelHarnessProtocol,  # noqa: ARG002
    ) -> Action.BeforeHarnessResult:
        self()

    @contextmanager
    def on_model_render(self) -> Iterator[None]:
        self()
        yield

    def __call__(self) -> None:
        sys.exit(0)
