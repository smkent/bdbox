"""ModelWatcher tests."""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from bdbox.runner.runner import ModelRunner
from bdbox.runner.watcher import ModelWatcher

if TYPE_CHECKING:
    from bdbox.actions.action import Action


@dataclass
class Modules:
    monkeypatch: pytest.MonkeyPatch
    tmp_path: Path
    ref_type: str
    model_ref: str | Path = field(init=False)
    mods_kept: dict[str, ModuleType] = field(default_factory=dict, init=False)
    mods_removed: dict[str, ModuleType] = field(
        default_factory=dict, init=False
    )

    def __post_init__(self) -> None:
        (self.local_dir / "model.py").write_text("")
        if self.ref_type == "file":
            self.model_ref = self.local_dir / "model.py"
        elif self.ref_type == "module":
            self.model_ref = "module_dir.local_dir.model"
        else:
            raise ValueError(self.ref_type)

    @contextmanager
    def __call__(self, watcher: ModelWatcher) -> Iterator[None]:
        yield
        sys_filter = {
            m
            for m in sys.modules
            if (m in self.mods_kept or m in self.mods_removed)
        }
        assert set(self.mods_kept.keys()).issubset(sys_filter)
        assert {
            Path(f).resolve()
            for p in self.mods_removed
            if (f := (self.mods_removed[p].__file__))
        }.issubset(watcher.watched_files)
        assert not set(self.mods_removed.keys()) & sys_filter

    def import_all(self) -> None:
        self._add("_local_mod", self.local_dir / "local_mod.py", kept=False)
        self._add(
            "_another_local_mod", self.local_dir / "another.py", kept=False
        )
        self._add(
            "_nonlocal_mod",
            self.nonlocal_dir / "nonlocal_lib.py",
            kept=(self.ref_type == "file"),
        )
        self._add(
            "_site_mod",
            "/usr/lib/python3/site-packages/_test_sitemod/__init__.py",
            kept=True,
        )

    def _add(self, name: str, path: str | Path, *, kept: bool = False) -> None:
        mod = ModuleType(name)
        mod.__file__ = str(Path(path).resolve())
        self.monkeypatch.setitem(sys.modules, name, mod)
        (self.mods_kept if kept else self.mods_removed)[name] = mod

    @cached_property
    def module_dir(self) -> Path:
        return self._mkmodule(self.tmp_path / "module_dir")

    @cached_property
    def local_dir(self) -> Path:
        return self._mkmodule(self.module_dir / "local_dir")

    @cached_property
    def nonlocal_dir(self) -> Path:
        return self._mkmodule(self.module_dir / "nonlocal_dir")

    def _mkmodule(self, newdir: Path) -> Path:
        newdir.mkdir()
        (newdir / "__init__.py").touch(exist_ok=True)
        return newdir


@pytest.fixture(params=("file", "module"))
def modules(
    request: pytest.FixtureRequest,
    ensure_sys_modules: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Modules:
    monkeypatch.syspath_prepend(tmp_path)
    return Modules(monkeypatch, tmp_path, ref_type=request.param)


ExpectExit = Callable[[Callable[[], None]], Callable[[], None]]


@pytest.fixture
def expect_exit() -> ExpectExit:
    def wrapper(fn: Callable[[], None]) -> Callable[[], None]:
        def func() -> None:
            with pytest.raises(SystemExit):
                fn()

        return func

    return wrapper


@pytest.fixture(autouse=True)
def mock_runner_call() -> Iterator[MagicMock]:
    with patch.object(ModelRunner, "__call__") as mocked:
        yield mocked


@pytest.fixture
def runner(
    tmp_path: Path, modules: Modules, mock_runner_call: MagicMock
) -> ModelRunner:
    return ModelRunner(modules.model_ref)


@pytest.fixture
def watcher(modules: Modules, runner: ModelRunner) -> Iterator[ModelWatcher]:
    watcher = ModelWatcher(runner)
    with modules(watcher):
        yield watcher


@pytest.fixture(autouse=True)
def mock_sleep() -> Iterator[MagicMock]:
    with patch.object(time, "sleep") as mocked:
        yield mocked


@pytest.fixture(
    params=(
        pytest.param(0, id="no_debounce"),
        pytest.param(1, id="debounce_1"),
        pytest.param(5, id="debounce_5"),
    )
)
def debounce(
    request: pytest.FixtureRequest,
    watcher: ModelWatcher,
    mock_sleep: MagicMock,
) -> Iterator[int]:
    count = request.param

    def _sleep(secs: float) -> None:
        if count and mock_sleep.call_count <= count:
            watcher.change_event.set()

    mock_sleep.side_effect = _sleep

    yield request.param
    assert mock_sleep.call_count == (count + 1)


@pytest.mark.usefixtures("debounce")
def test_runloop_with_rerun(
    expect_exit: ExpectExit,
    mock_runner_call: MagicMock,
    watcher: ModelWatcher,
    modules: Modules,
) -> None:
    """After the first run, runloop() blocks until change_event is set."""
    first_run_done = threading.Event()

    # Subclass threading.Event with a wait start signal
    @dataclass
    class _SignalingEvent(threading.Event):
        waiting: threading.Event = field(default_factory=threading.Event)

        def __post_init__(self) -> None:
            super().__init__()

        def wait(self, timeout: float | None = None) -> bool:
            self.waiting.set()
            return super().wait(timeout)

    def _call(action: Action | None = None) -> None:
        if mock_runner_call.call_count != 1:
            raise KeyboardInterrupt
        modules.import_all()
        first_run_done.set()

    mock_runner_call.side_effect = _call
    watcher.change_event = _SignalingEvent()

    t = threading.Thread(target=expect_exit(watcher.run), daemon=True)
    t.start()

    assert first_run_done.wait(timeout=1.0), "first run should have completed"
    assert watcher.change_event.waiting.wait(timeout=1.0), (
        "runloop should be waiting for change"
    )
    assert mock_runner_call.call_count == 1, (
        "runner should not have been called again yet"
    )
    watcher.change_event.set()
    t.join(timeout=1.0)

    assert mock_runner_call.call_count == 2
