from __future__ import annotations

from dataclasses import dataclass

from bdbox.viewer import ViewerManager

from .action import Action


@dataclass
class ViewerAction(Action):
    pass


@dataclass
class Start(ViewerAction):
    """Start the OCP CAD Viewer."""

    restart: bool = False
    open_browser: bool = True

    def before_harness(self) -> None:
        ViewerManager(
            restart=self.restart, open_browser=self.open_browser
        ).start()


@dataclass
class Stop(ViewerAction):
    """Stop the OCP CAD Viewer."""

    def before_harness(self) -> None:
        ViewerManager().stop()


@dataclass
class Status(ViewerAction):
    """Show OCP CAD Viewer status."""

    def before_harness(self) -> None:
        ViewerManager().status()
