from __future__ import annotations

import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from bdbox.runner import env as runner_env
from bdbox.runner.env import ENV_VAR
from bdbox.runner.harness import ModelHarness

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from tests.utils import DisallowCallable


@dataclass
class EnvTest:
    tmp_path: Path
    monkeypatch: pytest.MonkeyPatch
    venv_dir: Path | None = None

    def __post_init__(self) -> None:
        assert self.venv.is_dir()

    @contextmanager
    def __call__(self) -> Iterator[Self]:
        self.monkeypatch.delenv(ENV_VAR, raising=False)
        self.monkeypatch.setattr(sys, "argv", ["bdbox", str(self.model_file)])
        yield self

    def run(self) -> ModelHarness:
        return ModelHarness([str(self.model_file)])

    @contextmanager
    def assert_spec(self, *, spec: bool = False) -> Iterator[MagicMock]:
        with patch.object(runner_env, "find_spec", return_value=spec) as mock:
            yield mock
        mock.assert_called_once()

    def assert_exec(self) -> None:
        with (
            patch.object(os, "execv", side_effect=SystemExit) as mock_execv,
            pytest.raises(SystemExit),
        ):
            self.run()
        argv = [self.venv_python, "-m", "bdbox", str(self.model_file)]
        mock_execv.assert_called_once_with(argv[0], argv)

    @cached_property
    def project_dir(self) -> Path:
        path = self.tmp_path / "src"
        path.mkdir()
        return path

    @cached_property
    def model_file(self) -> Path:
        path = self.project_dir / "model.py"
        path.write_text("#/usr/bin/env python3")
        return path

    @cached_property
    def venv(self) -> Path:
        venv = self.venv_dir or (self.project_dir / ".venv")
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("home = /usr/bin\n")
        bin_dir = venv / ("Scripts" if os.name == "nt" else "bin")
        bin_dir.mkdir()
        (bin_dir / ("python.exe" if os.name == "nt" else "python")).touch()
        return venv

    @cached_property
    def venv_python(self) -> str:
        return str(
            self.venv
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )

    def set_venv_path(self, new_path: Path) -> None:
        shutil.rmtree(self.venv)
        del self.venv
        self.venv_dir = new_path
        assert self.venv.is_dir()


@pytest.fixture
def env_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[EnvTest]:
    with EnvTest(tmp_path=tmp_path, monkeypatch=monkeypatch)() as env:
        yield env


def test_reinvokes_when_venv_found_with_bdbox(env_test: EnvTest) -> None:
    with env_test.assert_spec(spec=True):
        env_test.assert_exec()


def test_no_reinvoke_when_no_venv(env_test: EnvTest) -> None:
    shutil.rmtree(env_test.venv)
    env_test.run()


def test_no_reinvoke_when_already_in_venv_python(env_test: EnvTest) -> None:
    env_test.monkeypatch.setattr(sys, "executable", env_test.venv_python)
    env_test.run()


def test_no_reinvoke_when_bdbox_not_in_venv(env_test: EnvTest) -> None:
    with env_test.assert_spec(spec=False):
        env_test.run()


def test_no_reinvoke_when_env_var_set(env_test: EnvTest) -> None:
    env_test.monkeypatch.setenv(ENV_VAR, env_test.venv_python)
    with env_test.assert_spec(spec=True):
        env_test.run()


def test_reinvokes_venv_in_parent_dir(env_test: EnvTest) -> None:
    env_test.set_venv_path(env_test.tmp_path / ".venv")
    with env_test.assert_spec(spec=True):
        env_test.assert_exec()


def test_reinvokes_venv_custom_name(env_test: EnvTest) -> None:
    env_test.set_venv_path(env_test.project_dir / "myenv")
    with env_test.assert_spec(spec=True):
        env_test.assert_exec()


@pytest.mark.parametrize(
    "module_name",
    ["nonexistent.module.for.env.test", "tests.models.params_export"],
)
def test_no_reinvoke_for_modules_same_env(
    env_test: EnvTest, module_name: str
) -> None:
    ModelHarness([module_name])


def test_reinvokes_for_modules_different_env(env_test: EnvTest) -> None:
    other_project = env_test.project_dir.parent / "other_project"
    shutil.copytree(env_test.project_dir, other_project)
    env_test.monkeypatch.chdir(env_test.project_dir)
    with env_test.assert_spec(spec=True):
        env_test.assert_exec()


def test_reinvokes_with_poetry_venv(
    disallow_os_exec: DisallowCallable, env_test: EnvTest
) -> None:
    (env_test.project_dir / "pyproject.toml").write_text(
        "[tool.poetry]\nname = 'test'\n"
    )
    env_test.set_venv_path(env_test.tmp_path / "poetry-env")
    poetry_venv = Path(env_test.venv_python).parent.parent

    def _output(cmd: Sequence[str], **kwargs: Any) -> str:
        if cmd == ["poetry", "env", "info", "--path"]:
            return f"{poetry_venv}\n"
        return "true\n"

    with patch.object(subprocess, "check_output", side_effect=_output):
        env_test.assert_exec()
