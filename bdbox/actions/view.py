"""View action."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Literal

import tyro

from bdbox.errors import MultipleModelsError, ParamsError, UsageError
from bdbox.model.serializer import serializer
from bdbox.protocol import (
    ModelDetailsMessage,
    ModelRunStatusMessage,
)
from bdbox.runner.runner import ModelRunner
from bdbox.runner.state import run_state
from bdbox.runner.watcher import ModelWatcher
from bdbox.view.app import ViewApp

from .action import ModelAction
from .export import ExportAction

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bdbox.model.info import ModelInfo


@dataclass
class ViewAction(ModelAction):
    """View model geometry in OCP CAD Viewer."""

    open_browser: Annotated[
        bool,
        tyro.conf.arg(
            aliases=("-b",),
            help="Open browser automatically",
            help_behavior_hint="(default: no)",
        ),
        tyro.conf.FlagCreatePairsOff,
    ] = False
    export: Annotated[
        Path | None,
        tyro.conf.arg(
            aliases=("-e",), metavar="DIR", help="Export output directory."
        ),
    ] = None
    format: Annotated[
        Literal["step", "stl"],
        tyro.conf.arg(aliases=["-f"], help="Output format."),
    ] = "step"
    server_port: Annotated[
        int,
        tyro.conf.arg(
            aliases=("-p",),
            metavar="port",
            help="Port for UI server to listen on (0 for automatic selection)",
        ),
    ] = 4040

    view_app: tyro.conf.Suppress[ViewApp | None] = None

    def __call__(self) -> None:
        """Collect geometry for viewer."""
        if self.view_app and (view_state := self.view_app.view_state):
            view_state.geometry = run_state.geometry
            view_state.show()
        if self.export:
            ExportAction(output=self.export, format=self.format)()

    def on_harness(self, model: ModelInfo) -> None:
        if not (model_arg := model.arg):
            raise UsageError("No model specified")
        self.view_app = ViewApp(
            server_port=self.server_port,
            model_class=model.params_class,
            open_browser=self.open_browser,
        )
        runner = ModelRunner([model_arg, *model.argv], self)
        ModelWatcher(
            runner=runner,
            change_event=self.view_app.view_state.rerender_event,
        )

    def _update_schema(self) -> None:
        if not self.view_app:
            return
        view_state = self.view_app.view_state
        try:
            new_class = run_state.model_state.get_model()
        except (ParamsError, MultipleModelsError):
            new_class = None
        new_schema = serializer.json_schema(new_class)
        old_schema = serializer.json_schema(view_state.model_class)
        view_state.params.values = serializer.unstructure(
            run_state.model_state.params.values
        )
        view_state.model_class = new_class
        self.view_app.enqueue(
            ModelDetailsMessage(
                model_info=run_state.model_state.model,
                schema=new_schema if new_schema != old_schema else None,
                params=view_state.params,
            )
        )

    @contextmanager
    def on_model_render(self) -> Iterator[None]:
        self._ensure_runner()
        with super().on_model_render() as timer:
            if not self.view_app:
                yield
                return
            view_state = self.view_app.view_state
            run_state.model_state.params.overrides = dict(
                view_state.params.overrides
            )
            self.view_app.enqueue(
                ModelRunStatusMessage.running(timer.started_at)
            )
            try:
                yield
            except (Exception, SystemExit):
                timer.stop()
                self.view_app.enqueue(
                    ModelRunStatusMessage.error(elapsed_ms=timer.elapsed_ms)
                )
                raise
            else:
                timer.stop()
                self.view_app.enqueue(
                    ModelRunStatusMessage.done(elapsed_ms=timer.elapsed_ms)
                )
                self._update_schema()
