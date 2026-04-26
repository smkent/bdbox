"""View action tests."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from bdbox.runner.harness import ModelHarness
from bdbox.runner.runner import ModelRunner
from bdbox.runner.watcher import ModelWatcher
from bdbox.viewer import ViewerManager

from .utils import MockOcpVscode, Models

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


pytestmark = pytest.mark.usefixtures("mock_ocp_vscode")


@pytest.fixture(autouse=True)
def mock_start() -> Iterator[MagicMock]:
    with patch.object(ViewerManager, "start") as mocked:
        yield mocked


@pytest.fixture(
    params=[
        pytest.param(Models.MODEL_EXPORT, id="Model"),
        pytest.param(Models.PARAMS_EXPORT, id="Params"),
    ]
)
def model(request: pytest.FixtureRequest) -> Path:
    return request.param


def test_embedded_mode_execs_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", [str(Models.MODEL_EXPORT), "view"])
    with (
        patch.object(subprocess, "run") as mock_run,
        pytest.raises(SystemExit),
    ):
        ModelRunner([Models.MODEL_EXPORT, "view"])()
    mock_run.assert_called_once_with(
        [sys.executable, "-m", "bdbox", str(Models.MODEL_EXPORT), "view"]
    )


def test_view_starts_watcher(model: Path) -> None:
    with patch.object(ModelWatcher, "run") as mock_run:
        ModelHarness([str(model), "view"])()
    mock_run.assert_called_once_with()


@pytest.mark.usefixtures("harness_mode")
def test_view_no_watch_skips_watcher(
    mock_start: MagicMock, model: Path
) -> None:
    with patch.object(ModelWatcher, "run") as mock_run:
        ModelHarness([str(model), "view", "--no-watch"])()
    mock_run.assert_not_called()
    mock_start.assert_called_once()


@pytest.mark.usefixtures("harness_mode")
def test_send_geometry_to_viewer(
    capsys: pytest.CaptureFixture[str],
    mock_ocp_vscode: MockOcpVscode,
) -> None:
    with patch.object(mock_ocp_vscode, "show") as mock_show:
        ModelRunner([Models.PARAMS_EXPORT, "view"])()
    mock_show.assert_called_once()
    assert len(mock_show.call_args[0][0]) == 1
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize("file_format", ["step", "stl"])
def test_view_with_export_creates_file(
    tmp_path: Path, model: Path, file_format: str
) -> None:
    output_file = tmp_path / f"out.{file_format}"
    ModelHarness(
        [str(model), "view", "--no-watch", "--export", str(output_file)]
    )()
    assert output_file.exists()


def test_send_to_viewer_warns_on_empty_geometry(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    mock_ocp_vscode: MockOcpVscode,
) -> None:
    model = tmp_path / "model.py"
    model.write_text('print("nope")')
    with patch.object(
        ModelWatcher,
        "run",
        autospec=True,
        side_effect=lambda self: self.runner(),
    ):
        ModelHarness([str(model), "view"])()
    assert "Warning: no geometry collected" in capsys.readouterr().err
