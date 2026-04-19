"""STEP file export tests."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import pytest

from bdbox.runner.runner import ModelRunner
from tests.test_invocation import MODELS_DIR

if TYPE_CHECKING:
    from collections.abc import Sequence


MAIN_STUB = MODELS_DIR / "main_stub.py"
MODEL_EXPORT = MODELS_DIR / "model_export.py"
PARAMS_EXPORT = MODELS_DIR / "params_export.py"
PLAIN_EXPORT = MODELS_DIR / "plain_export.py"


@dataclass
class ExportModelRunner:
    file_format: str
    output_file: Path = field(init=False)
    tmp_path: InitVar[str | Path]

    _FILE_HEADERS: ClassVar[dict] = {
        "step": "ISO-10303-21;",
        "stl": "STL Exported by Open CASCADE Technology [dev.opencascade.org]",
    }

    def __post_init__(self, tmp_path: str | Path) -> None:
        self.output_file = Path(tmp_path) / f"out.{self.file_format}"

    def __call__(self, filename: str | Path, argv: Sequence[Any]) -> None:
        ModelRunner.create_and_run_stub(filename, [str(a) for a in argv])
        assert self.output_file.exists()
        assert self.output_file.read_text(
            encoding="utf-8", errors="ignore"
        ).startswith(self._FILE_HEADERS[self.file_format])


@pytest.fixture(params=(pytest.param("step"), pytest.param("stl")))
def model_runner(
    request: pytest.FixtureRequest, tmp_path: Path
) -> ExportModelRunner:
    return ExportModelRunner(file_format=request.param, tmp_path=tmp_path)


@pytest.fixture(
    params=[
        pytest.param(MODEL_EXPORT, id="Model"),
        pytest.param(PARAMS_EXPORT, id="Params"),
    ]
)
def model(request: pytest.FixtureRequest) -> Path:
    return request.param


def test_model_export_embedded(
    model: Path, model_runner: ExportModelRunner
) -> None:
    model_runner(model, ["export", model_runner.output_file])


def test_export_with_parameters_after(
    model: Path, model_runner: ExportModelRunner
) -> None:
    model_runner(model, ["export", model_runner.output_file, "--size", "20"])


def test_export_with_parameters_before(
    model: Path, model_runner: ExportModelRunner
) -> None:
    model_runner(model, ["--size", "20", "export", model_runner.output_file])


def test_export_no_output_arg(
    model: Path, model_runner: ExportModelRunner
) -> None:
    with pytest.raises(ModelRunner.ExitError):
        model_runner(model, ["--size", "20", "export"])


@pytest.mark.parametrize(
    "model_file",
    [
        pytest.param(MODEL_EXPORT, id="Model"),
        pytest.param(PARAMS_EXPORT, id="Params"),
        pytest.param(PLAIN_EXPORT, id="plain"),
    ],
)
def test_harness_export(
    model_file: Path, model_runner: ExportModelRunner
) -> None:
    model_runner(MAIN_STUB, ["export", model_file, model_runner.output_file])


def test_harness_export_with_parameters(
    model: Path, model_runner: ExportModelRunner
) -> None:
    model_runner(
        MAIN_STUB, ["export", model, model_runner.output_file, "--size", "20"]
    )


def test_harness_export_no_model(model_runner: ExportModelRunner) -> None:
    with pytest.raises(ModelRunner.ExitError):
        model_runner(MAIN_STUB, ["export"])
