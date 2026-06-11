"""View action."""

from __future__ import annotations

import io
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Literal

import tyro

from bdbox.console import log
from bdbox.dispatch import Event
from bdbox.errors import MultipleModelsError, ParamsError, UsageError
from bdbox.protocol import (
    ModelDetailsMessage,
    ModelRunStatusMessage,
)
from bdbox.runner.runner import ModelRunner
from bdbox.runner.state import run_state
from bdbox.runner.watcher import ModelWatcher
from bdbox.serializer import serializer
from bdbox.view.server import ServerManager
from bdbox.view.state import ViewState
from bdbox.viewer import ViewerManager

from .action import ModelAction
from .export import ExportAction

if TYPE_CHECKING:
    from collections.abc import Iterator

    from build123d import Compound, Shape

    from bdbox.model.info import ModelInfo


@dataclass
class ViewAction(ModelAction):
    """View model geometry in OCP CAD Viewer."""

    watch: Annotated[
        bool,
        tyro.conf.arg(
            help="Watch and rerender model on changes",
            help_behavior_hint="(default: yes)",
        ),
        tyro.conf.FlagCreatePairsOff,
    ] = True
    restart_viewer: Annotated[
        bool,
        tyro.conf.arg(
            aliases=("-r",),
            help="Restart OCP CAD Viewer if already running",
            help_behavior_hint="(default: no)",
        ),
        tyro.conf.FlagCreatePairsOff,
    ] = False
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
            help="Port for UI server to listen on",
        ),
    ] = 4040

    server_manager: tyro.conf.Suppress[ServerManager | None] = None
    rerender_event: tyro.conf.Suppress[Event] = field(
        default_factory=lambda: Event(name="rerender_event"),
        init=False,
        repr=False,
    )

    def __call__(self) -> None:
        """Send collected geometry to the viewer."""
        geometry = run_state.geometry.resolve()
        if not geometry:
            log.warning("No geometry collected")
            return
        self.show(geometry)
        if self.export:
            ExportAction(output=self.export, format=self.format)()

    def show(self, geometry: Compound | Shape) -> None:
        from ocp_vscode import show  # noqa: PLC0415

        log.debug("Sending geometry to viewer")
        buf = io.StringIO()
        try:
            with redirect_stdout(buf), redirect_stderr(buf):
                show(geometry)
        finally:
            if ocp_vscode_output := buf.getvalue().strip():
                log.debug(ocp_vscode_output)

    def on_harness(self, model: ModelInfo) -> None:
        viewer = ViewerManager(restart=self.restart_viewer, open_browser=False)
        viewer.start()
        if self.watch:
            self.server_manager = ServerManager(
                port=self.server_port,
                view_state=ViewState(
                    rerender_event=self.rerender_event,
                    viewer_port=viewer.port,
                    model_class=model.params_class,
                ),
                open_browser=self.open_browser,
            )
        if not (model_arg := model.arg):
            raise UsageError("No model specified")
        runner = ModelRunner([model_arg, *model.argv], self)
        if self.watch:
            ModelWatcher(runner=runner, change_event=self.rerender_event).run()
            return
        runner.preserve_exceptions = True
        runner.run_or_exit()

    def _update_schema(self, ctx: ViewState) -> None:
        try:
            new_class = run_state.model_state.get_model()
        except (ParamsError, MultipleModelsError):
            new_class = None
        new_schema = serializer.json_schema(new_class)
        old_schema = serializer.json_schema(ctx.model_class)
        ctx.params.values = serializer.unstructure(
            run_state.model_state.params.values
        )
        ctx.model_class = new_class
        ctx.enqueue(
            ModelDetailsMessage(
                model_info=run_state.model_state.model,
                schema=new_schema if new_schema != old_schema else None,
                params=ctx.params,
            )
        )

    @contextmanager
    def on_model_render(self) -> Iterator[None]:
        self._ensure_runner()
        with super().on_model_render() as timer:
            if not self.server_manager:
                yield
                return
            ctx = self.server_manager.view_state
            run_state.model_state.params.overrides = dict(ctx.params.overrides)
            ctx.enqueue(ModelRunStatusMessage.running(timer.started_at))
            try:
                yield
            except (Exception, SystemExit):
                timer.stop()
                ctx.enqueue(
                    ModelRunStatusMessage.error(elapsed_ms=timer.elapsed_ms)
                )
                raise
            else:
                timer.stop()
                ctx.enqueue(
                    ModelRunStatusMessage.done(elapsed_ms=timer.elapsed_ms)
                )
                self._update_schema(ctx)
