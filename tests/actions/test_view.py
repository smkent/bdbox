"""View action tests."""

from __future__ import annotations

import os
import subprocess
import sys
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from bdbox.runner.harness import ModelHarness
from bdbox.runner.runner import ModelRunner
from bdbox.runner.watcher import ModelWatcher
from tests.utils import MockOcpVscode, Models, RaisesRunError

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


pytestmark = pytest.mark.usefixtures(
    "cache_build123d",
    "mock_ocp_vscode",
    "mock_server_start",
    "mock_ocp_cad_viewer_start",
    "mock_watch_run_once",
)


@dataclass
class ViewExportCase:
    export: bool
    output: Path | None = None
    args: Sequence[str] = ()

    def assert_no_geometry(self) -> None:
        if not self.export:
            return
        assert self.output
        assert not self.output.exists()


@pytest.fixture(
    params=[
        pytest.param(False, id="no_export"),
        pytest.param(True, id="export"),
    ]
)
def view_export_case(
    tmp_path: Path, request: pytest.FixtureRequest
) -> ViewExportCase:
    if request.param:
        output = tmp_path / "out"
        return ViewExportCase(
            export=True, output=output, args=["--export", str(output)]
        )
    return ViewExportCase(export=False)


@pytest.fixture(
    params=[
        pytest.param(Models.MODEL_EXPORT, id="Model"),
        pytest.param(Models.PARAMS_EXPORT, id="Params"),
    ]
)
def model(request: pytest.FixtureRequest) -> Path:
    return request.param


@dataclass
class MockShow(ExitStack):
    mock_ocp_vscode: MockOcpVscode
    show: MagicMock = field(init=False)
    show_clear: MagicMock = field(init=False)

    def __post_init__(self) -> None:
        super().__init__()

    def __enter__(self) -> Self:
        self.show = self.enter_context(
            patch.object(self.mock_ocp_vscode, "show")
        )
        self.show_clear = self.enter_context(
            patch.object(self.mock_ocp_vscode, "show_clear")
        )
        return super().__enter__()


@pytest.fixture
def mock_show(mock_ocp_vscode: MockOcpVscode) -> Iterator[MockShow]:
    with MockShow(mock_ocp_vscode=mock_ocp_vscode) as mock:
        yield mock


@pytest.mark.usefixtures("embedded_mode")
def test_embedded_mode_execs_harness() -> None:
    with (
        patch.object(subprocess, "run") as mock_run,
        RaisesRunError(SystemExit),
    ):
        ModelRunner([Models.MODEL_EXPORT, "view"])()
    mock_run.assert_called_once_with(
        [sys.executable, "-m", "bdbox", str(Models.MODEL_EXPORT), "view"]
    )


def test_view_without_model_does_not_start_watcher() -> None:
    with (
        patch.object(ModelWatcher, "start") as mock_watcher,
        pytest.raises(SystemExit),
    ):
        ModelHarness(["view"])()
    mock_watcher.assert_not_called()


def test_view_starts_watcher(model: Path) -> None:
    with patch.object(ModelWatcher, "start") as mock_watcher:
        ModelHarness([str(model), "view"])()
    mock_watcher.assert_called_once_with()


def test_model_view_passes_flags_to_server(
    model: Path,
    mock_server_start: MagicMock,
    mock_ocp_cad_viewer_start: MagicMock,
) -> None:
    ModelHarness([str(model), "view"])()
    mock_server_start.assert_called_once()
    mock_ocp_cad_viewer_start.assert_called_once()
    server_instance = mock_server_start.call_args[0][0]
    assert server_instance.open_browser is False


def test_send_geometry_to_viewer(mock_show: MockShow) -> None:
    ModelHarness([Models.PARAMS_EXPORT, "view"])()
    mock_show.show.assert_called_once()
    mock_show.show_clear.assert_not_called()
    assert len(mock_show.show.call_args[0][0]) == 3


@pytest.mark.parametrize("file_format", ["step", "stl"])
def test_view_with_export_creates_file(
    tmp_path: Path, model: Path, file_format: str
) -> None:
    output_file = tmp_path / "out"
    ModelHarness(
        [
            str(model),
            "view",
            "--export",
            str(output_file),
            "--format",
            file_format,
        ]
    )()
    assert output_file.is_dir()
    exported_files = list(output_file.iterdir())
    assert len(exported_files) == 7
    assert all(f.suffix == f".{file_format}" for f in exported_files)


def test_send_to_viewer_warns_on_empty_geometry(
    tmp_path: Path, log: pytest.LogCaptureFixture, mock_show: MockShow
) -> None:
    model = tmp_path / "model.py"
    model.write_text('print("nope")')
    ModelHarness([str(model), "view"])()
    mock_show.show.assert_not_called()
    mock_show.show_clear.assert_called_once_with()
    assert "No geometry collected" in log.messages
    assert "Sending geometry to viewer" not in log.messages


def test_send_to_viewer_shows_geometry_on_run_failure(
    tmp_path: Path, mock_show: MockShow, view_export_case: ViewExportCase
) -> None:
    model = tmp_path / "model.py"
    model.write_text(
        os.linesep.join(
            (
                "from build123d import Box",
                "from bdbox import show",
                "show(Box(77, 1138, 2187))",
                "raise RuntimeError('that\\'s no moon')",
            )
        )
    )
    with RaisesRunError(RuntimeError):
        ModelHarness([str(model), "view", *view_export_case.args])()
    mock_show.show.assert_called_once()
    mock_show.show_clear.assert_not_called()
    view_export_case.assert_no_geometry()


def test_send_to_viewer_clears_on_run_failure_with_no_geometry(
    tmp_path: Path, mock_show: MockShow, view_export_case: ViewExportCase
) -> None:
    model = tmp_path / "model.py"
    model.write_text("raise RuntimeError('no droids')")
    with RaisesRunError(RuntimeError):
        ModelHarness([str(model), "view", *view_export_case.args])()
    mock_show.show.assert_not_called()
    mock_show.show_clear.assert_called_once_with()
    view_export_case.assert_no_geometry()


@pytest.mark.parametrize(
    "model_file",
    [
        pytest.param(Models.MONO_MODEL_EXPORT, id="mono_model_export"),
        pytest.param(Models.MONO_PARAMS_EXPORT, id="mono_params_export"),
    ],
)
@pytest.mark.parametrize("select", ["nothing", "vertices", "edges", "faces"])
def test_view_with_export_no_geometry(
    tmp_path: Path,
    model_file: Path,
    log: pytest.LogCaptureFixture,
    select: str,
) -> None:
    output_file = tmp_path / "out"
    ModelHarness(
        [model_file, "view", "--export", str(output_file), "--select", select]
    )()
    assert not output_file.exists() or not any(output_file.iterdir())
    if select == "nothing":
        assert "Export: No geometry to export" in log.messages
    else:
        assert "Export: No solid geometry to export" in log.messages
