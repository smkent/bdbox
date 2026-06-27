"""OCP CAD Viewer management tests."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from bdbox.actions.view import ViewAction
from bdbox.view import ocp_cad_viewer
from tests.utils import ExecMain, Models

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path


pytestmark = pytest.mark.usefixtures(
    "cache_build123d", "mock_server_start", "mock_watch_run_once"
)


@pytest.fixture(
    params=[
        pytest.param(Models.MODEL_EXPORT, id="Model"),
        pytest.param(Models.PARAMS_EXPORT, id="Params"),
    ]
)
def model(request: pytest.FixtureRequest) -> Path:
    return request.param


@pytest.fixture(autouse=True)
def mock_urlopen() -> Iterator[MagicMock]:
    with patch.object(ocp_cad_viewer, "urlopen") as mocked:
        yield mocked


@pytest.fixture
def mock_popen() -> Iterator[MagicMock]:
    with patch.object(subprocess, "Popen") as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_browser_open() -> Iterator[MagicMock]:
    with patch.object(webbrowser, "open_new_tab") as mocked:
        yield mocked


@pytest.fixture(autouse=True)
def mock_view_action_on_model_render() -> Iterator[MagicMock]:
    @contextmanager
    def on_model_render() -> Iterator[None]:
        yield

    with patch.object(
        ViewAction, "on_model_render", side_effect=on_model_render
    ) as mocked:
        yield mocked


@pytest.fixture
def popen_kwargs() -> Mapping[str, Any]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def test_model_view_starts_ocp_cad_viewer(
    model: Path,
    exec_main: ExecMain,
    mock_popen: MagicMock,
    mock_server_start: MagicMock,
    popen_kwargs: Mapping[str, Any],
) -> None:
    exec_main(str(model), "view")
    mock_popen.assert_called_once_with(
        [sys.executable, "-u", "-m", "ocp_vscode", "--theme=dark"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        **popen_kwargs,
    )
    mock_server_start.assert_called_once()


def test_model_view_without_model_does_not_start_ocp_cad_viewer(
    exec_main: ExecMain, mock_popen: MagicMock, mock_server_start: MagicMock
) -> None:
    with pytest.raises(SystemExit):
        exec_main("view")
    mock_popen.assert_not_called()
    mock_server_start.assert_not_called()
