"""View action."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

from bdbox.geometry import resolve_geometry

from .action import ModelAction


@dataclass
class ViewAction(ModelAction):
    """View model geometry in OCP CAD Viewer."""

    watch: bool = True
    start_viewer: bool = True
    restart_viewer: bool = False
    open_browser: bool = True

    def __call__(self) -> None:
        """Send collected geometry to the viewer."""
        geometry = resolve_geometry()
        if not geometry:
            print("Warning: no geometry collected", file=sys.stderr)  # noqa: T201
        from ocp_vscode import show  # noqa: PLC0415

        show(geometry)

    def before_model(self) -> None:
        self._ensure_runner()
        if not self.start_viewer:
            return
        from bdbox.viewer import ViewerManager  # noqa: PLC0415

        ViewerManager(
            restart=self.restart_viewer,
            open_browser=self.open_browser,
        ).start()

    def _ensure_runner(self) -> None:
        if self.mode != self.Mode.HARNESS:
            try:
                returncode = subprocess.run(  # noqa: S603, PLW1510
                    [sys.executable, "-m", "bdbox", *sys.argv]
                ).returncode
            except KeyboardInterrupt:
                sys.exit(130)
            except Exception:  # noqa: BLE001
                sys.exit(2)
            sys.exit(returncode)
