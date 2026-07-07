"""View action tests."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from bdbox.runner.harness import ModelHarness
from bdbox.runner.runner import ModelRunner
from bdbox.runner.watcher import ModelWatcher
from tests.utils import MockOcpVscode, Models, RaisesRunError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


pytestmark = pytest.mark.usefixtures(
    "cache_build123d",
    "ensure_sys_modules",
    "mock_ocp_vscode",
    "mock_server_start",
    "mock_ocp_cad_viewer_start",
    "mock_watch_run_once",
)


@pytest.fixture(
    params=[
        pytest.param(Models.MODEL_EXPORT, id="Model"),
        pytest.param(Models.PARAMS_EXPORT, id="Params"),
    ]
)
def model(request: pytest.FixtureRequest) -> Path:
    return request.param


HarnessWrapper = Callable[..., ModelHarness]


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch) -> HarnessWrapper:

    def wrapper(
        model_argv: Sequence[str], *args: Any, **kwargs: Any
    ) -> ModelHarness:
        monkeypatch.setattr(sys, "argv", [model_argv[0], *model_argv])
        return ModelHarness(model_argv, *args, **kwargs)

    return wrapper


@pytest.mark.usefixtures("embedded_mode")
def test_embedded_mode_execs_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", [str(Models.MODEL_EXPORT), "view"])
    with (
        patch.object(subprocess, "run") as mock_run,
        RaisesRunError(SystemExit),
    ):
        ModelRunner([Models.MODEL_EXPORT, "view"])()
    mock_run.assert_called_once_with(
        [sys.executable, "-m", "bdbox", str(Models.MODEL_EXPORT), "view"]
    )


def test_view_without_model_does_not_start_watcher(
    harness: HarnessWrapper,
) -> None:
    with (
        patch.object(ModelWatcher, "start") as mock_watcher,
        pytest.raises(SystemExit),
    ):
        harness(["view"])()
    mock_watcher.assert_not_called()


def test_view_starts_watcher(model: Path, harness: HarnessWrapper) -> None:
    with patch.object(ModelWatcher, "start") as mock_watcher:
        harness([str(model), "view"])()
    mock_watcher.assert_called_once_with()


def test_model_view_passes_flags_to_server(
    model: Path,
    harness: HarnessWrapper,
    mock_server_start: MagicMock,
    mock_ocp_cad_viewer_start: MagicMock,
) -> None:
    harness([str(model), "view"])()
    mock_server_start.assert_called_once()
    mock_ocp_cad_viewer_start.assert_called_once()
    server_instance = mock_server_start.call_args[0][0]
    assert server_instance.open_browser is False


def test_send_geometry_to_viewer(
    mock_ocp_vscode: MockOcpVscode, harness: HarnessWrapper
) -> None:
    with patch.object(mock_ocp_vscode, "show") as mock_show:
        harness([Models.PARAMS_EXPORT, "view"])()
    mock_show.assert_called_once()
    assert len(mock_show.call_args[0][0]) == 2


@pytest.mark.parametrize("file_format", ["step", "stl"])
def test_view_with_export_creates_file(
    tmp_path: Path, model: Path, harness: HarnessWrapper, file_format: str
) -> None:
    output_file = tmp_path / "out"
    harness(
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
    assert len(exported_files) == 3
    assert all(f.suffix == f".{file_format}" for f in exported_files)


def test_send_to_viewer_warns_on_empty_geometry(
    tmp_path: Path,
    log: pytest.LogCaptureFixture,
    mock_ocp_vscode: MockOcpVscode,
    harness: HarnessWrapper,
) -> None:
    model = tmp_path / "model.py"
    model.write_text('print("nope")')
    harness([str(model), "view"])()
    assert "No geometry collected" in log.messages
    assert "Sending geometry to viewer" not in log.messages
