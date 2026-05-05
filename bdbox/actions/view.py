"""View action."""

from __future__ import annotations

import sys
import time
import traceback
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated

import tyro

from bdbox.errors import MultipleModelsError, ParamsError
from bdbox.geometry import resolve_geometry
from bdbox.parameters.state import run_state
from bdbox.server.console import tee_stderr
from bdbox.server.context import Context
from bdbox.server.server import ServerManager
from bdbox.viewer import ViewerManager

from .action import ModelAction
from .export import ExportAction

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass
class ViewAction(ModelAction):
    """View model geometry in OCP CAD Viewer."""

    watch: bool = True
    start_viewer: bool = True
    restart_viewer: bool = False
    open_browser: bool = True

    export: Annotated[
        Path | None,
        tyro.conf.arg(
            aliases=("-e",),
            metavar="output-path",
            help="Output STEP or STL file path.",
        ),
    ] = None

    server_manager: tyro.conf.Suppress[ServerManager | None] = None

    def __call__(self) -> None:
        """Send collected geometry to the viewer."""
        geometry = resolve_geometry()
        if not geometry:
            print("Warning: no geometry collected", file=sys.stderr)  # noqa: T201
        from ocp_vscode import show  # noqa: PLC0415

        print("Sending model geometry to viewer")  # noqa: T201
        show(geometry)

        if self.export:
            ExportAction(output=self.export)()

    def before_harness(
        self, args: ModelAction.ModelHarnessProtocol
    ) -> ModelAction.BeforeHarnessResult:
        if not self.start_viewer:
            return

        viewer = ViewerManager(restart=self.restart_viewer, open_browser=False)
        viewer.start()
        self.server_manager = ServerManager(
            context=Context(
                rerender_event=args.rerender_event,
                viewer_port=viewer.port,
                model_class=args.model_params_cls,
            ),
            open_browser=self.open_browser,
        ).start()

    def watch_end(self) -> None:
        if self.server_manager:
            self.server_manager.stop()

    def _update_schema(self, ctx: Context) -> None:
        try:
            new_class = run_state.get_model()
        except (ParamsError, MultipleModelsError):
            new_class = None
        new_schema = new_class.schema() if new_class else {}
        old_schema = ctx.model_class.schema() if ctx.model_class else {}
        ctx.current_values = dict(run_state.resolved_values)
        if new_schema != old_schema:
            ctx.model_class = new_class
            ctx.msg_queue.put({"type": "schema", "schema": new_schema})

    @contextmanager
    def on_model_render(self) -> Iterator[None]:
        self._ensure_runner()
        if not self.server_manager:
            yield
            return
        ctx = self.server_manager.context
        run_state.param_overrides = dict(ctx.param_overrides)
        start_time = time.monotonic()
        ctx.msg_queue.put(
            {"type": "run_start", "params": dict(ctx.param_overrides)}
        )
        tee = tee_stderr(ctx.msg_queue) if ctx else nullcontext()
        try:
            with tee:
                yield
            elapsed = int((time.monotonic() - start_time) * 1000)
            self._update_schema(ctx)
            ctx.msg_queue.put(
                {
                    "type": "run_ok",
                    "elapsed_ms": elapsed,
                    "current_values": dict(run_state.resolved_values),
                }
            )
        except (Exception, SystemExit):
            if ctx:
                tb = traceback.format_exc()
                ctx.msg_queue.put({"type": "run_error", "traceback": tb})
            raise
