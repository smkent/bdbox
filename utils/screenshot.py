from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import tyro

from bdbox.cli import CLIOptions
from bdbox.errors import UsageError
from utils.demo import DEMO_MODEL, AppBrowserSession

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from playwright.sync_api import (
        ViewportSize,
    )


@dataclass
class RecordScreenshot:
    @dataclass
    class CLI(CLIOptions):
        output: Annotated[
            tyro.conf.Positional[Path],
            tyro.conf.arg(
                metavar="output-file", help="Screenshot output PNG file"
            ),
        ] = Path("screenshot.png")
        headless: Annotated[
            bool,
            tyro.conf.arg(
                aliases=("-H",),
                help="Run with browser window visible",
                help_behavior_hint="(default: headless)",
            ),
            tyro.conf.FlagCreatePairsOff,
        ] = field(default=True)
        width: Annotated[
            int, tyro.conf.arg(aliases=("-x",), help="Viewport width")
        ] = 1280
        height: Annotated[
            int, tyro.conf.arg(aliases=("-y",), help="Viewport height")
        ] = 800

        @classmethod
        def parse_args(cls) -> Self:
            args = tyro.cli(cls)
            if not args.output.suffix:
                args.output = args.output.with_suffix(".png")
            if args.output.suffix != ".png":
                raise UsageError("Output file must have a `.png` extension")
            if isinstance(args, CLIOptions):
                args.configure()
            return args

        @property
        def viewport_size(self) -> ViewportSize:
            return {"width": self.width, "height": self.height}

    args: CLI = field(default_factory=CLI.parse_args, init=False)
    app: AppBrowserSession = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.app = AppBrowserSession(
            model=DEMO_MODEL,
            args=self.args,
            headless=self.args.headless,
            viewport_size=self.args.viewport_size,
            show_cursor=False,
        )

    def __call__(self) -> None:
        subprocess.run(["poe", "static"], check=True)
        with self.app:
            self.app.set_param("display_color-color", "lime")
            self.app.page.wait_for_timeout(500)
            self.app.set_param("width", 40)
            self.app.page.wait_for_timeout(500)
            self.app.viewer_click_iso()
            self.app.viewer_click_resize()
            self.app.page.wait_for_timeout(100)
            self.app.page.screenshot(path=self.args.output)


if __name__ == "__main__":
    RecordScreenshot()()
