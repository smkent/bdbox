from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property
from threading import Event as StdlibEvent
from threading import Thread as StdlibThread
from typing import TYPE_CHECKING, Any

from bdbox.console import excepthook, log

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence


@dataclass
class Service(ABC):
    @abstractmethod
    def start(self) -> None:
        dispatch.on_exit(self.stop)

    @abstractmethod
    def stop(self) -> None:
        pass


@dataclass
class Event(StdlibEvent):
    name: str | None = None

    def __post_init__(self) -> None:
        super().__init__()

    def set(self) -> None:
        log.trace("Set event %s", self.name or self)
        return super().set()

    def clear(self) -> None:
        log.trace("Clear event %s", self.name or self)
        return super().clear()


@dataclass(repr=False)
class Thread(StdlibThread):
    group: None = field(default=None, init=False, repr=False)
    target: Callable[..., Any] | None = None
    name: str | None = None
    args: Sequence[Any] = ()
    kwargs: Mapping[str, Any] | None = None
    daemon: bool | None = None

    __hash__ = object.__hash__

    def __post_init__(self) -> None:
        super().__init__(
            group=self.group,
            target=self.target,
            name=self.name,
            args=self.args,
            kwargs=self.kwargs,
            daemon=self.daemon,
        )
        if not self.name:
            self.name = self._name  # ty: ignore[unresolved-attribute]

    def run(self) -> None:
        log.trace("Thread start")
        try:
            super().run()
        except BaseException:
            dispatch.exit.set()
            raise
        finally:
            log.trace("Thread complete")

    def start(self) -> None:
        dispatch.threads.append(self)
        return super().start()

    def join(self, timeout: float | None = None) -> None:
        super().join(timeout=timeout)
        if self.is_alive():
            log.trace("Thread still alive after join: %s", self.name)


@dataclass
class Dispatch:
    @dataclass
    class ExitCallback:
        name: str | None = field(default=None, kw_only=True)
        callback: Callable[[], None] = field(repr=False)

        @cached_property
        def display_name(self) -> str:
            return self.name or self.callback.__qualname__  # ty: ignore[unresolved-attribute]

    exit: Event = field(default_factory=lambda: Event(name="exit"))
    exit_callbacks_thread: Thread | None = None
    exit_callbacks: list[ExitCallback] = field(default_factory=list)
    threads: list[Thread] = field(default_factory=list)

    def reset(self) -> None:
        """Reset state for tests."""
        self.__init__()

    def on_exit(
        self, callback: Callable[[], None], *, name: str | None = None
    ) -> None:
        ec = self.ExitCallback(callback=callback, name=name)
        if self.exit.is_set():
            log.warning(
                "Attempted exit callback registration after exit set: %s",
                ec.display_name,
            )
            callback()
            return
        if not self.exit_callbacks_thread:

            def _run() -> None:
                self.exit.wait()
                count = len(self.exit_callbacks)
                log.trace("Run %d callbacks", count)
                for i, ec in enumerate(reversed(self.exit_callbacks)):
                    log.trace(
                        "Run callback %d / %d: %s",
                        i + 1,
                        count,
                        ec.display_name,
                    )
                    try:
                        ec.callback()
                    except BaseException:  # noqa: BLE001
                        excepthook(*sys.exc_info(), self.exit_callbacks_thread)  # ty: ignore[invalid-argument-type]

            self.exit_callbacks_thread = Thread(
                target=_run, daemon=True, name="exit-callbacks"
            )
            self.exit_callbacks_thread.start()
        self.exit_callbacks.append(ec)
        log.trace("Registered exit callback: %s", ec.display_name)

    def exit_join(self) -> None:
        count = len(self.threads)
        log.trace("Joining %d threads", count)
        if self.threads:
            for i, thread in enumerate(reversed(self.threads)):
                log.trace(
                    "Joining thread %d / %d: %s", i + 1, count, thread.name
                )
                thread.join()
            log.trace("Joined %d threads", count)
            self.threads = []


dispatch = Dispatch()
