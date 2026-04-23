from __future__ import annotations

import random
import subprocess
import sys
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from bdbox.actions.action import Action
from bdbox.runner.utils import reset_bdbox

from .utils import DisallowCallable, MockBuild123d, MockOcpVscode

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(scope="session", autouse=True)
def cache_build123d() -> None:
    """Import build123d at session scope for reuse across tests."""
    import build123d  # noqa: F401, PLC0415


@pytest.fixture(scope="session", autouse=True)
def random_seed() -> None:
    random.Random(1138_2187)  # noqa: S311


@pytest.fixture(autouse=True)
def reset_all() -> None:
    """Reset all bdbox state before each test."""
    reset_bdbox()
    Action.mode = Action.Mode.EMBEDDED


@pytest.fixture(autouse=True)
def disallow_subprocess(
    request: pytest.FixtureRequest,
) -> Iterator[DisallowCallable]:
    with DisallowCallable(request, subprocess.Popen, "__init__")() as mock:
        yield mock


@pytest.fixture
def harness_mode() -> Iterator[None]:
    with patch.object(Action, "mode", Action.Mode.HARNESS):
        yield


@pytest.fixture
def mock_b123d(monkeypatch: pytest.MonkeyPatch) -> MockBuild123d:
    module = MockBuild123d()
    monkeypatch.setitem(sys.modules, "build123d", module)
    return module


@pytest.fixture(autouse=True)
def mock_ocp_vscode(monkeypatch: pytest.MonkeyPatch) -> MockOcpVscode:
    module = MockOcpVscode()
    monkeypatch.setitem(sys.modules, "ocp_vscode", module)
    monkeypatch.setitem(sys.modules, "ocp_vscode.comms", module.comms)
    return module
