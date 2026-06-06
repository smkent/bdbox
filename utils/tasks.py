from __future__ import annotations

import subprocess
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from rich import print  # noqa: A004
from rich.text import Text

pty = None
with suppress(ImportError):
    import pty

if TYPE_CHECKING:
    from collections.abc import Sequence


def run(cmd: Sequence[str]) -> bool:
    cmd_text = Text(" ".join(cmd), style="color(153)")
    fn = Path(__file__)
    txt = Text.assemble(
        Text(f"{fn.relative_to(fn.parent.parent)} => ", style="bold"),
        cmd_text,
    )
    print(txt)
    if pty:
        return pty.spawn(cmd) == 0
    return subprocess.run(cmd).returncode == 0  # noqa: S603, PLW1510


def install_playwright_tools() -> None:
    cmd = ["uv", "run", "playwright", "install", "--with-deps", "chromium"]
    if not run(cmd):
        print()
        print(
            Text(
                "Automatic playwright tools installation did not succeed."
                " Please run manually:",
                style="red bold",
            )
        )
        print()
        print(
            Text()
            .append("    $ ", style="blue bold")
            .append(" ".join(cmd), style="bold")
        )
        print()
