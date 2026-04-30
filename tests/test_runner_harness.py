"""ModelLocator module cleanup behavior tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bdbox.runner.harness import ModelHarness

from .utils import Models

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion


pytestmark = pytest.mark.usefixtures("ensure_sys_modules")


@dataclass
class HarnessRunnerRunner:
    capsys: pytest.CaptureFixture[str]
    snapshot: SnapshotAssertion
    module: str

    def __call__(self, *args: str) -> None:
        with pytest.raises(SystemExit):
            ModelHarness([self.module, *args])()
        assert self.capsys.readouterr().out == self.snapshot


@pytest.fixture
def model_runner(
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
    module: str,
) -> HarnessRunnerRunner:
    return HarnessRunnerRunner(capsys=capsys, snapshot=snapshot, module=module)


@pytest.fixture(
    params=[
        pytest.param(Models.MOD_PARAMS, id="params"),
        pytest.param(Models.MOD_MODEL, id="model"),
        pytest.param(Models.MOD_PLAIN, id="plain"),
        pytest.param(Models.MONO_PARAMS, id="mono_params"),
        pytest.param(Models.MONO_MODEL, id="mono_model"),
        pytest.param(Models.MONO_PLAIN, id="mono_plain"),
    ]
)
def module(request: pytest.FixtureRequest) -> str:
    return request.param


def test_harness_usage(model_runner: HarnessRunnerRunner) -> None:
    model_runner("--help")


def test_successive_harness_success(model_runner: HarnessRunnerRunner) -> None:
    for _ in range(2):
        model_runner("--help")


def test_harness_existing_non_model_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (test_file := Path("some.unrelated.file")).write_text("Hello there")
    with pytest.raises(SystemExit):
        ModelHarness([str(test_file)])()
    assert capsys.readouterr().err == snapshot
