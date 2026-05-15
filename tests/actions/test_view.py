"""View action tests."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

import bdbox.view.server as server_module
from bdbox.actions.action import Action
from bdbox.actions.view import ViewAction
from bdbox.errors import RunError
from bdbox.runner.harness import ModelHarness
from bdbox.runner.runner import ModelRunner
from bdbox.runner.watcher import ModelWatcher
from bdbox.viewer import ViewerManager
from tests.utils import MockOcpVscode, Models

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path


pytestmark = pytest.mark.usefixtures("ensure_sys_modules", "mock_ocp_vscode")


@pytest.fixture(autouse=True)
def mock_start() -> Iterator[MagicMock]:
    with patch.object(ViewerManager, "start") as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_server_start() -> Iterator[MagicMock]:
    with patch.object(
        server_module.ServerManager, "start", autospec=True
    ) as mocked:
        yield mocked


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


def test_embedded_mode_execs_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", [str(Models.MODEL_EXPORT), "view"])
    with (
        patch.object(subprocess, "run") as mock_run,
        pytest.raises(RunError),
    ):
        ModelRunner([Models.MODEL_EXPORT, "view"])()
    mock_run.assert_called_once_with(
        [sys.executable, "-m", "bdbox", str(Models.MODEL_EXPORT), "view"]
    )


def test_view_starts_watcher(model: Path, harness: HarnessWrapper) -> None:
    with patch.object(ModelWatcher, "run") as mock_run:
        harness([str(model), "view"])()
    mock_run.assert_called_once_with()


def test_view_no_watch_skips_watcher(
    mock_start: MagicMock, model: Path, harness: HarnessWrapper
) -> None:
    with patch.object(ModelWatcher, "run") as mock_run:
        harness([str(model), "view", "--no-watch"])()
    mock_run.assert_not_called()
    mock_start.assert_called_once()


def test_send_geometry_to_viewer(mock_ocp_vscode: MockOcpVscode) -> None:
    with (
        patch.object(Action, "mode", Action.Mode.HARNESS),
        patch.object(mock_ocp_vscode, "show") as mock_show,
    ):
        ModelRunner([Models.PARAMS_EXPORT, "view"], ViewAction())()
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
            "--no-watch",
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
    with patch.object(
        ModelWatcher,
        "run",
        autospec=True,
        side_effect=lambda self: self.runner(),
    ):
        harness([str(model), "view"])()
    assert "No geometry collected" in log.messages
    assert "Sending geometry to viewer" not in log.messages
