from __future__ import annotations

import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

STATIC_DIR = Path(__file__).parent / "bdbox/view/static"


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:  # noqa: ARG002
        subprocess.run(["npm", "ci"], check=True)
        subprocess.run(["npm", "run", "build"], check=True)
        build_data["artifacts"] += [
            str(p.relative_to(Path(__file__).parent))
            for p in STATIC_DIR.glob("*")
            if p.is_file()
        ]
