"""View action."""

from __future__ import annotations

import io
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Literal

import tyro

from bdbox.console import log
from bdbox.errors import MultipleModelsError, ParamsError
from bdbox.geometry import resolve_geometry
from bdbox.parameters.model_state import model_state
from bdbox.serializer import Serializer
from bdbox.view.server import ServerManager
from bdbox.view.view_state import ViewState
from bdbox.viewer import ViewerManager

from .action import ModelAction
from .export import ExportAction

if TYPE_CHECKING:
    from collections.abc import Iterator

    from build123d import Compound, Shape

serializer = Serializer()


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

    server_manager: tyro.conf.Suppress[ServerManager | None] = None

    def __call__(self) -> None:
        """Send collected geometry to the viewer."""
        geometry = resolve_geometry()
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

    def before_harness(
        self, args: ModelAction.ModelHarnessProtocol
    ) -> ModelAction.BeforeHarnessResult:
        viewer = ViewerManager(restart=self.restart_viewer, open_browser=False)
        viewer.start()
        if self.watch:
            self.server_manager = ServerManager(
                view_state=ViewState(
                    rerender_event=args.rerender_event,
                    viewer_port=viewer.port,
                    model_class=args.model_params_cls,
                ),
                open_browser=self.open_browser,
            ).start()

    def watch_end(self) -> None:
        if self.server_manager:
            self.server_manager.stop()

    def _update_schema(self, ctx: ViewState) -> None:
        try:
            new_class = model_state.get_model()
        except (ParamsError, MultipleModelsError):
            new_class = None
        new_schema = serializer.json_schema(new_class)
        old_schema = serializer.json_schema(ctx.model_class)
        ctx.current_values = dict(model_state.resolved_values)
        if new_schema != old_schema:
            ctx.model_class = new_class
            ctx.enqueue(
                {
                    "type": "schema",
                    "schema": new_schema,
                    "model_info": model_state.model_name_info(),
                }
            )

    @contextmanager
    def on_model_render(self) -> Iterator[None]:
        self._ensure_runner()
        with super().on_model_render() as timer:
            if not self.server_manager:
                yield
                return
            ctx = self.server_manager.view_state
            model_state.param_overrides = dict(ctx.param_overrides)
            ctx.enqueue(
                {"type": "run_start", "params": dict(ctx.param_overrides)}
            )
            log.info("Running model")
            try:
                yield
            except (Exception, SystemExit):
                ctx.enqueue({"type": "run_error", "elapsed_ms": timer.end})
                raise
            else:
                self._update_schema(ctx)
                ctx.enqueue(
                    {
                        "type": "run_ok",
                        "elapsed_ms": timer.end,
                        "current_values": dict(model_state.resolved_values),
                    }
                )
