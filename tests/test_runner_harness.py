"""ModelHarness behavior tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from bdbox.errors import MultipleModelsError, ParamsError
from bdbox.runner.harness import ModelHarness

from .utils import Models

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion


pytestmark = pytest.mark.usefixtures("ensure_sys_modules")


@dataclass
class HarnessRunnerRunner:
    capsys: pytest.CaptureFixture[str]
    snapshot: SnapshotAssertion

    def __call__(self, *args: str | Path) -> None:
        with pytest.raises(SystemExit):
            ModelHarness([*args])()
        assert self.capsys.readouterr().out == self.snapshot
        assert self.capsys.readouterr().err == self.snapshot


@pytest.fixture
def model_runner(
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> HarnessRunnerRunner:
    return HarnessRunnerRunner(capsys=capsys, snapshot=snapshot)


@pytest.fixture(
    params=[
        pytest.param(Models.MOD_PARAMS, id="params"),
        pytest.param(Models.MOD_MODEL, id="model"),
        pytest.param(Models.MOD_PLAIN, id="plain"),
        pytest.param(Models.MONO_PARAMS, id="mono_params"),
        pytest.param(Models.MONO_MODEL, id="mono_model"),
        pytest.param(Models.MONO_PLAIN, id="mono_plain"),
        pytest.param(f"{Models.MONO_PARAMS}:P", id="mono_params_class"),
        pytest.param(f"{Models.MONO_MODEL}:MyModel", id="mono_model_class"),
        pytest.param(f"{Models.MOD_PARAMS}:P", id="params_class"),
        pytest.param(f"{Models.MOD_MODEL}:SomeModel", id="model_class"),
    ]
)
def module(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture(
    params=[
        pytest.param(Models.MODEL_CLASS, id="model_class"),
        pytest.param(Models.PARAMS_CLASS, id="params_class"),
        pytest.param(Models.MODEL_EXPORT, id="model_export"),
        pytest.param(Models.PARAMS_EXPORT, id="params_export"),
        pytest.param(Models.PLAIN_EXPORT, id="plain_export"),
    ]
)
def model(request: pytest.FixtureRequest) -> str:
    return request.param


def test_harness_usage_module(
    model_runner: HarnessRunnerRunner, module: str
) -> None:
    model_runner(module, "--help")


def test_harness_usage_file(
    model_runner: HarnessRunnerRunner, model: str
) -> None:
    model_runner(model, "--help")


def test_successive_harness_success(
    model_runner: HarnessRunnerRunner, module: str
) -> None:
    for _ in range(2):
        model_runner(module, "--help")


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


@pytest.mark.parametrize(
    "model",
    [
        pytest.param(
            Models.MIXED_MODEL_THEN_PARAMS, id="mixed_model_then_params"
        ),
        pytest.param(
            Models.MIXED_PARAMS_THEN_MODEL, id="mixed_params_then_model"
        ),
    ],
)
def test_harness_mixed_modes(
    model_runner: HarnessRunnerRunner, model: str
) -> None:
    with pytest.raises(ParamsError, match=r"Cannot .* with an existing"):
        model_runner(model)


@pytest.mark.parametrize(
    "model",
    [
        pytest.param(Models.MODEL_CLASS_MULTIPLE.stem, id="multiple"),
        pytest.param(Models.MODEL_CLASS.stem, id="single"),
    ],
)
def test_harness_no_class_found(
    model_runner: HarnessRunnerRunner, model: str
) -> None:
    with pytest.raises(ParamsError):
        model_runner(f"tests.models.{model}:NoModel")


def test_harness_multiple_models(model_runner: HarnessRunnerRunner) -> None:
    with pytest.raises(MultipleModelsError, match="FirstModel, SecondModel"):
        model_runner(Models.MODEL_CLASS_MULTIPLE)
