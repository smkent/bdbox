"""STEP file export tests."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import InitVar, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Protocol
from unittest.mock import patch

import pytest

from bdbox.actions.export import ExportAction
from bdbox.errors import RunError
from bdbox.runner.harness import ModelHarness
from bdbox.runner.runner import ModelRunner
from tests.utils import Examples, Models, RaisesRunError

if TYPE_CHECKING:
    from collections.abc import Sequence


pytestmark = pytest.mark.usefixtures("cache_build123d", "mock_sys_modules")


MAIN_STUB = Models.DIR / "main_stub.py"


class Runner(Protocol):
    def __init__(
        self, model_argv: Sequence[Path | str] | Path | str = ()
    ) -> None: ...


@dataclass
class ExportModelRunner:
    file_format: Literal["step", "stl"]
    output_dir: Path = field(init=False)
    tmp_path: InitVar[str | Path]
    monkeypatch: pytest.MonkeyPatch
    caplog: pytest.LogCaptureFixture

    _FILE_HEADERS: ClassVar[dict] = {
        "step": "ISO-10303-21;",
        "stl": "STL Exported by Open CASCADE Technology [dev.opencascade.org]",
    }

    def __post_init__(self, tmp_path: str | Path) -> None:
        self.output_dir = Path(tmp_path) / "export"

    def __call__(
        self,
        filename: str | Path,
        argv: Sequence[Any],
        run_class: type[Runner] = ModelRunner,
        num_outputs: int = 1,
        *,
        single: bool = True,
    ) -> None:
        kwargs = {}
        if run_class is ModelRunner:
            kwargs["action"] = ExportAction(
                output=self.output_dir, single=single, format=self.file_format
            )
        args = [filename, *[str(a) for a in argv]]
        if self.file_format == "stl":
            args += ["--format", "stl"]
        self.monkeypatch.setattr(sys, "argv", args)
        run_class(args, **kwargs)()
        assert self.output_dir.exists()
        output_files = list(self.output_dir.iterdir())
        assert len(output_files) == num_outputs
        for output_file in output_files:
            format_header = self._FILE_HEADERS[self.file_format]
            file_header = output_file.read_text(
                encoding="utf-8", errors="ignore"
            )[: len(format_header)]
            assert file_header == format_header
        log_message_prefix = "Exporting model geometry to "
        assert {
            Path(m.removeprefix(log_message_prefix).strip())
            for m in self.caplog.messages
            if log_message_prefix in m
        } == set(output_files)


@dataclass
class RunClass:
    cls: type[Runner]
    exc_type: type[Exception] | None = None


@pytest.fixture(
    params=(
        pytest.param(RunClass(ModelHarness), id="harness"),
        pytest.param(RunClass(ModelRunner, RunError), id="runner"),
    )
)
def run_class_info(request: pytest.FixtureRequest) -> RunClass:
    return request.param


@pytest.fixture
def run_class(run_class_info: RunClass) -> type[Runner]:
    return run_class_info.cls


@pytest.fixture(params=(pytest.param("step"), pytest.param("stl")))
def model_runner(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> ExportModelRunner:
    return ExportModelRunner(
        file_format=request.param,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        caplog=caplog,
    )


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
        pytest.param(Models.MODEL_SUBMODULE_EXPORT, id="model_submodule"),
        pytest.param(Models.PARAMS_EXPORT, id="Params"),
        pytest.param(Models.PARAMS_SUBMODULE_EXPORT, id="params_submodule"),
        pytest.param(Models.MONO_MODEL, id="mono_model"),
        pytest.param(Models.MONO_PARAMS, id="mono_params"),
        pytest.param(Models.MONO_PLAIN, id="mono_plain"),
        pytest.param(f"{Models.MONO_PARAMS}:P", id="mono_params_class"),
        pytest.param(f"{Models.MONO_MODEL}:MyModel", id="mono_model_class"),
    ]
)
def model(request: pytest.FixtureRequest) -> Path:
    return request.param


def test_model_export(
    run_class: type[Runner], model: Path, model_runner: ExportModelRunner
) -> None:
    model_runner(
        model,
        ["export", "--single", model_runner.output_dir],
        run_class=run_class,
        single=True,
    )


@pytest.mark.usefixtures("embedded_mode")
def test_export_with_parameters_after(
    run_class: type[Runner],
    model_with_params: Path,
    model_runner: ExportModelRunner,
) -> None:
    model_runner(
        model_with_params,
        ["export", model_runner.output_dir, "--size", "20"],
        run_class=run_class,
        num_outputs=3,
    )


@pytest.mark.usefixtures("embedded_mode")
def test_export_with_parameters_before(
    run_class: type[Runner],
    model_with_params: Path,
    model_runner: ExportModelRunner,
) -> None:
    model_runner(
        model_with_params,
        ["--size", "20", "export", model_runner.output_dir],
        run_class=run_class,
        num_outputs=3,
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
    model_runner(
        MAIN_STUB,
        ["export", model_file, model_runner.output_dir],
        num_outputs=3,
    )


def test_main_export_with_parameters(
    model_with_params: Path, model_runner: ExportModelRunner
) -> None:
    model_runner(
        MAIN_STUB,
        [
            "export",
            model_with_params,
            model_runner.output_dir,
            "--size",
            "20",
        ],
        num_outputs=3,
    )


def test_main_export_no_model(model_runner: ExportModelRunner) -> None:
    with RaisesRunError(SystemExit):
        model_runner(MAIN_STUB, ["export"])


@pytest.mark.usefixtures("embedded_mode")
def test_export_all_embedded_execs_harness(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    argv = [
        str(Models.PARAMS_EXPORT),
        "export",
        "-a",
        str(tmp_path),
        "--format",
        "step",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    with (
        patch.object(subprocess, "run") as mock_run,
        RaisesRunError(SystemExit),
    ):
        ModelRunner(
            [
                Models.PARAMS_EXPORT,
                "export",
                "-a",
                str(tmp_path),
                "--format",
                "step",
            ]
        )()
    mock_run.assert_called_once_with([sys.executable, "-m", "bdbox", *argv])


@pytest.mark.usefixtures("embedded_mode")
def test_export_single_embedded_does_not_exec_harness(
    tmp_path: Path, model_runner: ExportModelRunner
) -> None:
    with patch.object(subprocess, "run") as mock_run:
        model_runner(
            Models.PARAMS_EXPORT,
            ["export", model_runner.output_dir],
            num_outputs=3,
        )
    mock_run.assert_not_called()


@pytest.mark.parametrize(
    ("model_file", "expected_stems"),
    [
        pytest.param(
            Models.PARAMS_EXPORT,
            [
                Models.PARAMS_EXPORT.stem,
                f"{Models.PARAMS_EXPORT.stem}.Box",
                f"{Models.PARAMS_EXPORT.stem}.Box_002",
                f"{Models.PARAMS_EXPORT.stem}-mid",
                f"{Models.PARAMS_EXPORT.stem}-mid.Box",
                f"{Models.PARAMS_EXPORT.stem}-mid.Box_002",
            ],
            id="Params-with-preset",
        ),
        pytest.param(
            Models.MODEL_EXPORT,
            [
                "ExportModel",
                "ExportModel.Box",
                "ExportModel.Box_002",
                "ExportModel-mid",
                "ExportModel-mid.Box",
                "ExportModel-mid.Box_002",
            ],
            id="Model-with-preset",
        ),
        pytest.param(
            Models.PLAIN_EXPORT,
            [
                Models.PLAIN_EXPORT.stem,
                f"{Models.PLAIN_EXPORT.stem}.Box",
                f"{Models.PLAIN_EXPORT.stem}.Box_002",
            ],
            id="plain-no-presets",
        ),
        pytest.param(
            Examples.BOX_DEMO,
            [
                "BoxDemo",
                "BoxDemo-chamfer-cube",
                "BoxDemo-cube",
                "BoxDemo-lime-chamfer-cube",
                "BoxDemo-thin",
            ],
            id="examples-demo",
        ),
    ],
)
@pytest.mark.parametrize("file_format", ["step", "stl"])
def test_export_all_creates_preset_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    model_file: Path,
    expected_stems: list[str],
    file_format: Literal["step", "stl"],
) -> None:
    out_dir = tmp_path / "renders"
    args = [
        str(model_file),
        "export",
        "-a",
        str(out_dir),
        "--format",
        file_format,
    ]
    monkeypatch.setattr(sys, "argv", args)
    ModelHarness(args)()
    assert out_dir.is_dir()
    assert sorted(p.stem for p in out_dir.iterdir()) == sorted(expected_stems)
    for stem in expected_stems:
        assert (out_dir / f"{stem}.{file_format}").exists()


def test_export_all_creates_output_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out_dir = tmp_path / "a" / "b" / "renders"
    assert not out_dir.exists()
    args = [
        str(Models.PLAIN_EXPORT),
        "export",
        "-a",
        str(out_dir),
        "--format",
        "step",
    ]
    monkeypatch.setattr(sys, "argv", args)
    ModelHarness(args)()
    monkeypatch.setattr(sys, "argv", args)
    assert out_dir.is_dir()
