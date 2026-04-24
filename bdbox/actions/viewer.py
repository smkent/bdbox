from __future__ import annotations

import sys
from dataclasses import dataclass

from bdbox.viewer import ViewerManager

from .action import Action


@dataclass
class ViewerAction(Action):
    def before_harness(self) -> None:
        self()

    def before_model(self) -> None:
        self()

    def __call__(self) -> None:
        sys.exit(0)


@dataclass
class Start(ViewerAction):
    """Start the OCP CAD Viewer."""

    restart: bool = False
    open_browser: bool = True

    def __call__(self) -> None:
        ViewerManager(
            restart=self.restart, open_browser=self.open_browser
        ).start()
        super().__call__()


@dataclass
class Stop(ViewerAction):
    """Stop the OCP CAD Viewer."""

    def __call__(self) -> None:
        ViewerManager().stop()
        super().__call__()


@dataclass
class Status(ViewerAction):
    """Show OCP CAD Viewer status."""

    def __call__(self) -> None:
        ViewerManager().status()
        super().__call__()
