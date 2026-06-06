from __future__ import annotations

import logging
import os
import random
import subprocess
import sys
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from bdbox.actions.action import Action
from bdbox.console import console
from bdbox.dispatch import dispatch
from bdbox.model.model import Model
from bdbox.model.parameters import Params
from bdbox.runner.state import run_state

pytest.register_assert_rewrite("tests.utils")

from tests.utils import (  # noqa: E402
    DisallowCallable,
    ExecMain,
    MockBuild123d,
    MockOcpVscode,
    ThreadExceptions,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--vv",
        type=int,
        action="store",
        metavar="level",
        default=-1,
        nargs="?",
        const=1,
        help="bdbox verbosity level (1 for -v, 2 for -vv, etc.)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "frontend: Playwright browser based web UI tests"
    )


@pytest.fixture(scope="session", autouse=True)
def cache_build123d() -> None:
    """Import build123d at session scope for reuse across tests."""
    import build123d  # noqa: F401, PLC0415


@pytest.fixture(scope="session", autouse=True)
def random_seed() -> None:
    random.Random(1138_2187)  # noqa: S311


@pytest.fixture(autouse=True)
def reset_all() -> Iterator[None]:
    """Reset all bdbox state before each test."""
    run_state.reset()
    dispatch.reset()
    Action.mode = Action.Mode.EMBEDDED
    yield
    dispatch.exit.set()
    dispatch.exit_join()


@pytest.fixture
def mock_sys_modules() -> Iterator[None]:
    with patch.dict(sys.modules, sys.modules.copy()):
        yield


@pytest.fixture
def ensure_sys_modules() -> Iterator[None]:
    mods = sys.modules.copy()
    with patch.dict(sys.modules, sys.modules.copy()):
        yield
        unexpected_modules = {
            mod
            for mod in (set(sys.modules.keys()) - set(mods.keys()))
            if mod == "tests.models" or mod.startswith("tests.models.")
        }
        assert not unexpected_modules


@pytest.fixture(autouse=True)
def disallow_subprocess(
    request: pytest.FixtureRequest,
) -> Iterator[DisallowCallable]:
    with DisallowCallable(request, subprocess.Popen, "__init__")() as mock:
        yield mock


@pytest.fixture(autouse=True)
def disallow_os_exec(
    request: pytest.FixtureRequest,
) -> Iterator[DisallowCallable]:
    with DisallowCallable(request, os, "execv")() as mock:
        yield mock


@pytest.fixture
def exec_main(monkeypatch: pytest.MonkeyPatch) -> ExecMain:
    return ExecMain(monkeypatch)


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


@pytest.fixture(
    params=(pytest.param(Params, id="Params"), pytest.param(Model, id="Model"))
)
def model_base(request: pytest.FixtureRequest) -> type[Params]:
    return request.param


@pytest.fixture
def log(
    caplog: pytest.LogCaptureFixture,
) -> Iterator[pytest.LogCaptureFixture]:
    with caplog.at_level(logging.DEBUG, logger="bdbox"):
        yield caplog


@pytest.fixture(autouse=True)
def console_verbosity(request: pytest.FixtureRequest) -> Iterator[None]:
    if (verbosity_level := request.config.getoption("--vv")) < 0:
        yield
        return

    original = console.configure

    def wrapper(**kwargs: Any) -> Any:
        kwargs["verbose"] = verbosity_level
        original(**kwargs)

    with patch.object(
        console, "configure", autospec=True, side_effect=wrapper
    ):
        yield


@pytest.fixture(autouse=True)
def thread_exceptions() -> Iterator[ThreadExceptions]:
    instance = ThreadExceptions()
    with instance.catch():
        yield instance
