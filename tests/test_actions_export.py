"""STEP file export tests."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

import pytest

from bdbox.actions.export import ExportAction
from bdbox.runner.harness import ModelHarness
from bdbox.runner.runner import ModelRunner

from .utils import Models

if TYPE_CHECKING:
    from collections.abc import Sequence


pytestmark = pytest.mark.usefixtures("mock_sys_modules")


MAIN_STUB = Models.DIR / "main_stub.py"


class Runner(Protocol):
    def __init__(
        self, model_argv: Sequence[Path | str] | Path | str = ()
    ) -> None: ...


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

    def __call__(
        self,
        filename: str | Path,
        argv: Sequence[Any],
        run_class: type[Runner] = ModelRunner,
    ) -> None:
        kwargs = {}
        if run_class is ModelRunner:
            kwargs["action"] = ExportAction(output=self.output_file)
        run_class([filename, *[str(a) for a in argv]], **kwargs)()
        assert self.output_file.exists()
        assert self.output_file.read_text(
            encoding="utf-8", errors="ignore"
        ).startswith(self._FILE_HEADERS[self.file_format])


@pytest.fixture(
    params=(
        pytest.param(ModelHarness, id="harness"),
        pytest.param(ModelRunner, id="runner"),
    )
)
def run_class(request: pytest.FixtureRequest) -> type[Runner]:
    return request.param


@pytest.fixture(params=(pytest.param("step"), pytest.param("stl")))
def model_runner(
    request: pytest.FixtureRequest, tmp_path: Path
) -> ExportModelRunner:
    return ExportModelRunner(file_format=request.param, tmp_path=tmp_path)


@pytest.fixture(
    params=[
        pytest.param(Models.MODEL_EXPORT, id="Model"),
        pytest.param(Models.PARAMS_EXPORT, id="Params"),
    ]
)
def model_with_params(request: pytest.FixtureRequest) -> Path:
    return request.param


@pytest.fixture(
    params=[
        pytest.param(Models.MODEL_EXPORT, id="Model"),
        pytest.param(Models.PARAMS_EXPORT, id="Params"),
        pytest.param(Models.MONO_MODEL, id="mono_model"),
        pytest.param(Models.MONO_PARAMS, id="mono_params"),
        pytest.param(Models.MONO_PLAIN, id="mono_plain"),
    ]
)
def model(request: pytest.FixtureRequest) -> Path:
    return request.param


def test_model_export(
    run_class: type[Runner], model: Path, model_runner: ExportModelRunner
) -> None:
    model_runner(
        model, ["export", model_runner.output_file], run_class=run_class
    )


def test_export_with_parameters_after(
    run_class: type[Runner],
    model_with_params: Path,
    model_runner: ExportModelRunner,
) -> None:
    model_runner(
        model_with_params,
        ["export", model_runner.output_file, "--size", "20"],
        run_class=run_class,
    )


def test_export_with_parameters_before(
    run_class: type[Runner],
    model_with_params: Path,
    model_runner: ExportModelRunner,
) -> None:
    model_runner(
        model_with_params,
        ["--size", "20", "export", model_runner.output_file],
        run_class=run_class,
    )


def test_export_no_output_arg(
    run_class: type[Runner],
    model_with_params: Path,
    model_runner: ExportModelRunner,
) -> None:
    with pytest.raises(SystemExit):
        model_runner(
            model_with_params, ["--size", "20", "export"], run_class=run_class
        )


@pytest.mark.parametrize(
    "model_file",
    [
        pytest.param(Models.MODEL_EXPORT, id="Model"),
        pytest.param(Models.PARAMS_EXPORT, id="Params"),
        pytest.param(Models.PLAIN_EXPORT, id="plain"),
    ],
)
def test_main_export(
    model_file: Path, model_runner: ExportModelRunner
) -> None:
    model_runner(MAIN_STUB, ["export", model_file, model_runner.output_file])


def test_main_export_with_parameters(
    model_with_params: Path, model_runner: ExportModelRunner
) -> None:
    model_runner(
        MAIN_STUB,
        [
            "export",
            model_with_params,
            model_runner.output_file,
            "--size",
            "20",
        ],
    )


def test_main_export_no_model(model_runner: ExportModelRunner) -> None:
    with pytest.raises(SystemExit):
        model_runner(MAIN_STUB, ["export"])
