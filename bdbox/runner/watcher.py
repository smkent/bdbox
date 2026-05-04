"""File watching and model hot-reload."""

from __future__ import annotations

import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from bdbox.errors import Error

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .runner import ModelRunner

_DEBOUNCE_SECS = 0.15


@dataclass
class ModelWatcher:
    """Tracks local module dependencies and signals on file changes."""

    runner: ModelRunner
    change_event: Event = field(default_factory=Event, repr=False)
    local_modules: dict[str, str] = field(default_factory=dict, init=False)
    started: bool = field(default=False, init=False)

    @property
    @contextmanager
    def observer(self) -> Iterator[None]:

        class _Handler(FileSystemEventHandler):
            def on_modified(_self, event: FileSystemEvent) -> None:  # noqa: N805
                if not event.is_directory:
                    p = Path(str(event.src_path)).resolve()
                    if p in self.watched_files:
                        self.change_event.set()

            def on_created(_self, event: FileSystemEvent) -> None:  # noqa: N805
                _self.on_modified(event)

        observer = Observer()
        observer.schedule(
            _Handler(), str(self.runner.model_base_dir), recursive=True
        )
        observer.start()
        yield
        observer.stop()
        observer.join(timeout=3.0)

    @cached_property
    def model_path(self) -> Path:
        if not self.runner.model_path:
            raise Error("Model path missing")
        return self.runner.model_path

    @property
    def watched_files(self) -> frozenset[Path]:
        """Current set of files to watch: model + local dependency files."""
        return frozenset(
            {self.model_path} | {Path(f) for f in self.local_modules.values()}
        )

    def run(self) -> None:
        with self.observer:
            try:
                while True:
                    self.wait_for_change()
                    with self.handle_modules:
                        try:
                            self.runner()
                        except (Exception, SystemExit):  # noqa: BLE001
                            traceback.print_exc()
            except KeyboardInterrupt:
                print("Quitting", file=sys.stderr)  # noqa: T201
            finally:
                if self.runner.action:
                    self.runner.action.watch_end()

    @property
    @contextmanager
    def handle_modules(self) -> Iterator[None]:
        self.evict_local_modules()
        before = self.snapshot_modules()
        yield
        self.update_local_modules(before)

    def snapshot_modules(self) -> set[str]:
        """Return a snapshot of current sys.modules keys before a run."""
        return set(sys.modules.keys())

    def update_local_modules(self, before: set[str]) -> None:
        """After run, add any newly imported modules local to the model dir."""
        for name in set(sys.modules) - before:
            if (mod := sys.modules.get(name)) is None:
                continue
            if not (f := getattr(mod, "__file__", None)):
                continue
            p = Path(f).resolve()
            if "site-packages" in p.parts:
                continue
            try:
                p.relative_to(self.runner.model_base_dir)
            except ValueError:
                continue
            self.local_modules[name] = str(p)

    def evict_local_modules(self) -> None:
        """Remove tracked local modules from sys.modules before a re-run."""
        for name in list(self.local_modules):
            sys.modules.pop(name, None)

    def wait_for_change(self) -> None:
        """Block the main thread until a file changes, with debounce."""
        if not self.started:
            self.started = True
            return
        self.change_event.wait()
        # Keep clearing and re-waiting until no new events arrive within the
        # debounce window. This handles editors that write multiple events per
        # save.
        while True:
            self.change_event.clear()
            time.sleep(_DEBOUNCE_SECS)
            if not self.change_event.is_set():
                break
