from __future__ import annotations

from dataclasses import dataclass

from bdbox.viewer import ViewerManager

from .action import CommandAction


@dataclass
class Start(CommandAction):
    """Start the OCP CAD Viewer."""

    restart: bool = False
    open_browser: bool = True

    def __call__(self) -> None:
        ViewerManager(
            restart=self.restart, open_browser=self.open_browser
        ).start()
        super().__call__()


@dataclass
class Stop(CommandAction):
    """Stop the OCP CAD Viewer."""

    def __call__(self) -> None:
        ViewerManager().stop()
        super().__call__()


@dataclass
class Status(CommandAction):
    """Show OCP CAD Viewer status."""

    def __call__(self) -> None:
        ViewerManager().status()
        super().__call__()
