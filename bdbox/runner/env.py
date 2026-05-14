from __future__ import annotations

import os
import subprocess
import sys
from contextlib import suppress
from dataclasses import InitVar, dataclass, field
from importlib.util import find_spec
from pathlib import Path

from bdbox.console import log

ENV_VAR = "BDBOX_FOUND_ENVIRONMENT"


@dataclass
class EnvLocator:
    target_file: InitVar[str | Path | None] = None
    target_dir: Path | None = field(default=None, init=False)
    target_module: str | None = None
    module: str = "bdbox"

    def __post_init__(self, target_file: str | Path | None) -> None:
        if target_file:
            if not (target_path := (Path(target_file).resolve())).exists():
                raise FileNotFoundError(f"{target_path} does not exist")
            if not (target_path.is_dir()):
                target_path = target_path.parent
            self.target_dir = target_path
        if self.target_module:
            self.target_dir = Path().cwd()

    def venv_python_if_module(self, project_dir: Path) -> Path | None:
        executable = (
            project_dir / "Scripts" / "python.exe"
            if os.name == "nt"
            else project_dir / "bin" / "python"
        )
        if not executable.exists():
            return None
        try:
            sys.path.insert(0, str(project_dir.parent))
            if find_spec("bdbox"):
                if self.target_module and find_spec(self.target_module):
                    self.exec(str(executable))
                return executable
        finally:
            sys.path.pop(0)
        return None

    def project_root(self) -> Path:
        if venv_dir := self.find_venv():
            return venv_dir.resolve().parent
        return Path.cwd()

    def find_venv(self) -> Path | None:
        if not self.target_dir:
            return None
        for search_dir in [self.target_dir, *self.target_dir.parents]:
            if (pyproject := (search_dir / "pyproject.toml")).exists():
                content = pyproject.read_text()
                if (
                    "[tool.poetry]" in content or "poetry-core" in content
                ) and (result := self.find_venv_from_poetry(search_dir)):
                    return result
            for child in search_dir.iterdir():
                if not child.is_dir():
                    continue
                with suppress(PermissionError):
                    if (child / "pyvenv.cfg").is_file():
                        return child
        return None

    def find_venv_from_poetry(self, project_dir: Path) -> Path | None:
        with suppress(subprocess.CalledProcessError):
            text = subprocess.check_output(
                ["poetry", "env", "info", "--path"], cwd=project_dir, text=True
            )
            if (found_dir := Path(text.strip()).resolve()).is_dir():
                return found_dir
        return None

    def exec(self, exec_executable: str) -> None:
        if existing_exe := os.environ.get(ENV_VAR):
            log.error(
                f"Already reinvoked with {existing_exe}!"
                " Preventing reinvocation loop."
            )
            return
        new_exec = [str(exec_executable), "-m", self.module, *sys.argv[1:]]
        os.environ[ENV_VAR] = str(exec_executable)
        os.execv(new_exec[0], new_exec)  # noqa: S606

    def ensure_env(self) -> None:
        if not (venv_dir := self.find_venv()):
            return
        if Path(sys.executable).parent.parent == venv_dir.resolve():
            return
        if exec_executable := self.venv_python_if_module(venv_dir):
            log.debug(f"Exec: {exec_executable}")
            self.exec(str(exec_executable))
        return
