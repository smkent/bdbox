from __future__ import annotations

import sys
from dataclasses import dataclass

from bdbox.viewer import ViewerManager

from .action import Action


@dataclass
class ViewerAction(Action):
    def before_model(self) -> None:
        sys.exit(0)


@dataclass
class Start(ViewerAction):
    """Start the OCP CAD Viewer."""

    restart: bool = False
    open_browser: bool = True

    def before_model(self) -> None:
        ViewerManager(
            restart=self.restart, open_browser=self.open_browser
        ).start()
        super().before_model()


@dataclass
class Stop(ViewerAction):
    """Stop the OCP CAD Viewer."""

    def before_model(self) -> None:
        ViewerManager().stop()
        super().before_model()


@dataclass
class Status(ViewerAction):
    """Show OCP CAD Viewer status."""

    def before_model(self) -> None:
        ViewerManager().status()
        super().before_model()
