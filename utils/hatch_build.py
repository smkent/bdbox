from __future__ import annotations

import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:  # noqa: ARG002
        subprocess.run(["npm", "ci"], check=True)
        subprocess.run(["npm", "run", "build"], check=True)
        build_data["artifacts"].append("bdbox/server/static/app.js")
