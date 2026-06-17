from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import tyro
from playwright.sync_api import (
    BrowserContext,
    Locator,
    Page,
    ViewportSize,
    expect,
    sync_playwright,
)

from bdbox.cli import CLIOptions
from bdbox.console import log
from bdbox.errors import InternalError, UsageError

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence
    from types import TracebackType


BDBOX_PORT = 65432
BDBOX_URL = f"http://localhost:{BDBOX_PORT}"
DEMO_MODEL = "bdbox.examples.demo"


@dataclass
class CallableContextManager(ABC):
    __context_manager: AbstractContextManager[Any] = field(init=False)

    @contextmanager
    @abstractmethod
    def __call__(self) -> Iterator[Any]: ...

    def __enter__(self) -> Self:
        self.__context_manager = self()
        self.__context_manager.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        return self.__context_manager.__exit__(exc_type, exc_val, exc_tb)


@dataclass
class AppBrowserSession(CallableContextManager):
    model: str
    args: CLIOptions | None = field(default=None)
    headless: bool = field(default=True, kw_only=True)
    page: Page = field(init=False, repr=False)
    viewport_size: ViewportSize = field(
        default_factory=lambda: {"width": 1280, "height": 800}
    )
    ocp_cad_viewer: Locator = field(init=False, repr=False)
    click_wait: float = field(default=0.0, repr=False)

    @contextmanager
    def __call__(self) -> Iterator[Self]:
        with self.new_page():
            yield self

    @contextmanager
    def screencast(self, output: Path) -> Iterator[None]:
        self.page.screencast.start(path=output)
        try:
            yield
        finally:
            self.page.screencast.stop()
            log.info('Screencast saved: "%s"', output)

    @contextmanager
    def bdbox_view(self) -> Iterator[None]:
        try:
            proc = subprocess.Popen(  # noqa: S603
                [
                    sys.executable,
                    "-m",
                    "bdbox",
                    "view",
                    self.model,
                    "--server-port",
                    str(BDBOX_PORT),
                    *(self.args.to_args() if self.args else []),
                ]
            )
            self._wait_for_url(BDBOX_URL)
            yield
        finally:
            proc.terminate()

    @contextmanager
    def new_page(self) -> Iterator[None]:
        log.debug("Starting browser session")
        with (
            self.bdbox_view(),
            sync_playwright() as p,
            p.chromium.launch(headless=self.headless) as browser,
            browser.new_context(viewport=self.viewport_size) as ctx,
            self.bdbox_page(ctx),
        ):
            self.page.wait_for_timeout(500)
            log.debug("Browser session ready")
            yield

    @contextmanager
    def bdbox_page(self, ctx: BrowserContext) -> Iterator[None]:
        with ctx.new_page() as page:
            self.page = page
            page.set_default_timeout(5_000)

            page.add_init_script(
                (Path(__file__).parent / "assets" / "cursor.js").read_text()
            )

            with self.page.expect_console_message(
                lambda msg: "WebSocket connection established" in msg.text,
                timeout=10_000,
            ):
                self.page.goto(BDBOX_URL)
            self.reset_params()
            self.ocp_cad_viewer = self.page.frame_locator(
                "iframe[src*='/viewer']"
            ).locator("#cad_viewer")
            self.ocp_cad_viewer.click()
            self.ocp_cad_viewer.press("p")
            self.ocp_cad_viewer.press("r")
            self.ocp_cad_viewer.press("5")
            yield

    def reset_params(self, *, wait: bool = True, resize: bool = False) -> None:
        self.move_click(self.page.locator(".params-reset-btn"))
        self._post_render(wait=wait, resize=resize)

    def set_preset(
        self, name: str, *, wait: bool = True, resize: bool = False
    ) -> None:
        self.move_click(self.page.get_by_role("button", name=name, exact=True))
        self._post_render(wait=wait, resize=resize)

    def set_param(
        self,
        name: str,
        value: Any = None,
        *,
        wait: bool = True,
        resize: bool = False,
    ) -> None:
        element = self.page.locator(f"#root-{name}")
        match element.evaluate("el => el.type.toLowerCase()"):
            case "checkbox":
                self.move_click(element)
            case "select-one":
                if value is None:
                    raise InternalError("Value is required")
                element.select_option(label=value)
            case "range":
                if (
                    value is None
                    or not isinstance(value, float)
                    or not (0 <= value <= 1)
                ):
                    raise InternalError(
                        "Value must be a float in the range 0.0 to 1.0"
                    )
                box = element.bounding_box()
                if not box:
                    raise InternalError("Slider bounding box missing")
                x = box["x"] + box["width"] * (float(value))
                y = box["y"] + box["height"] / 2
                self.page.mouse.click(x, y)
            case _:
                if value is None:
                    raise InternalError("Value is required")
                self.move_click(element)
                self.page.wait_for_timeout(50)
                element.fill(str(value))
        element.blur()
        self._post_render(wait=wait, resize=resize)

    def _post_render(self, *, wait: bool = True, resize: bool = False) -> None:
        if wait:
            expect(self.page.locator(".status-running")).to_be_visible()
            expect(self.page.locator(".status-ok")).to_be_visible()
        if resize:
            self.viewer_click_resize()

    def _wait_for_url(self, url: str, timeout: float = 10.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                urllib.request.urlopen(url, timeout=1)  # noqa: S310
            except urllib.error.URLError:  # noqa: PERF203
                time.sleep(0.5)
            else:
                return
        raise TimeoutError(f"Timed out waiting for {url}")

    def move_click(self, locator: Locator, delay_ms: int = 300) -> None:
        if not (box := locator.bounding_box()):
            return
        self.page.mouse.move(
            box["x"] + box["width"] / 2,
            box["y"] + box["height"] / 2,
        )
        if (wait_time := (self.click_wait - time.monotonic())) > 0:
            self.page.wait_for_timeout(int(wait_time))
        self.page.wait_for_timeout(delay_ms)
        locator.click()
        self.click_wait = time.monotonic() + 200

    def rotate_viewer(
        self,
        dx: float = 0.4,
        dy: float = 0.05,
        duration_ms: int = 60,
        ms_per_step: int = 10,
    ) -> None:
        if not (box := self.ocp_cad_viewer.bounding_box()):
            raise InternalError("Unable to determine viewer bounding box")
        if (wait_time := (self.click_wait - time.monotonic())) > 0:
            self.page.wait_for_timeout(int(wait_time))
        cx = box["x"] + box["width"] / 2
        cy = box["y"] + box["height"] / 2
        self.page.mouse.move(cx, cy)
        self.page.wait_for_timeout(200)
        self.page.mouse.down()
        steps = int(duration_ms / ms_per_step) + 1
        dx_pixels = int(dx * box["width"])
        dy_pixels = int(dy * box["height"])
        for i in range(1, steps + 1):
            self.page.mouse.move(
                cx + dx_pixels * i / steps,
                cy + dy_pixels * i / steps,
            )
            self.page.wait_for_timeout(duration_ms // steps)

        self.page.mouse.up()
        self.click_wait = time.monotonic() + 200

    def viewer_click_iso(self) -> None:
        self.move_click(self.ocp_cad_viewer.locator(".tcv_button_iso"))

    def viewer_click_resize(self) -> None:
        self.move_click(self.ocp_cad_viewer.locator(".tcv_button_resize"))


@dataclass
class RecordDemo:
    @dataclass
    class CLI(CLIOptions):
        output: Annotated[
            tyro.conf.Positional[Path],
            tyro.conf.arg(
                metavar="output-file", help="Screencast output WebM file"
            ),
        ] = Path("demo.webm")
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
                args.output = args.output.with_suffix(".webm")
            if args.output.suffix != ".webm":
                raise UsageError("Output file must have a `.webm` extension")
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
        )

    def __call__(self) -> None:
        subprocess.run(["poe", "static"], check=True)
        with self.app as session, session.screencast(self.args.output):
            self.record_demo()

    def wait(self, ms: int) -> None:
        self.app.page.wait_for_timeout(ms)

    def demo_action(
        self,
        action: Callable[[], None],
        wait_ms: int = 2000,
        move_viewer: Sequence[tuple[float, float]] | tuple[float, float] = (),
        *,
        iso: bool = False,
    ) -> None:
        if iso:
            self.app.viewer_click_iso()
        action()
        if (
            move_viewer
            and isinstance(move_viewer, tuple)
            and isinstance(move_viewer[0], float)
            and isinstance(move_viewer[1], float)
        ):
            moves: Sequence[tuple[float, float]] = [move_viewer]  # ty: ignore[invalid-assignment]
        else:
            moves: Sequence[tuple[float, float]] = move_viewer  # ty: ignore[invalid-assignment]
        if not isinstance(moves, (list, tuple)):
            raise InternalError("Invalid move_viewer values")
        for dx, dy in moves:
            self.app.rotate_viewer(dx=dx, dy=dy)
        if wait_ms:
            self.wait(wait_ms)

    def record_demo(self) -> None:
        self.demo_action(
            lambda: self.app.set_param("width", 40, resize=True),
            iso=True,
            wait_ms=500,
        )
        self.app.rotate_viewer(dx=0, dy=-0.05)
        self.demo_action(lambda: self.app.set_param("length", 40), wait_ms=500)
        self.demo_action(lambda: self.app.set_param("height", 20), wait_ms=500)
        self.demo_action(lambda: self.app.set_param("chamfer"), wait_ms=250)
        self.demo_action(
            lambda: self.app.set_param("fillet"),
            wait_ms=250,
        )
        self.wait(1000)
        for i, preset in enumerate(
            ("thin", "cube", "chamfer-cube", "lime-chamfer-cube")
        ):
            self.demo_action(
                partial(self.app.set_preset, preset, resize=(i == 0)),
                move_viewer=((0.025, -0.05) if i == 0 else ()),
                iso=(i == 0),
                wait_ms=500,
            )
            if i <= 1:
                self.app.viewer_click_resize()

        self.wait(1000)
        self.demo_action(lambda: self.app.reset_params(resize=True), iso=True)
        self.wait(2000)


if __name__ == "__main__":
    RecordDemo()()
