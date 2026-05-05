from __future__ import annotations

import sys
from dataclasses import dataclass

from .action import CommandAction


@dataclass
class VersionAction(CommandAction):
    def __call__(self) -> None:
        from bdbox import version  # noqa: PLC0415

        print(version)  # noqa: T201
        sys.exit(0)
