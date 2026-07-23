from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cached_property
from types import ModuleType
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from types import TracebackType


class Build123dStub(ModuleType, MagicMock):
    MC = 0.001
    MM = 1
    CM = 10 * MM
    M = 1000 * MM
    IN = 25.4 * MM
    FT = 12 * IN
    THOU = IN / 1000
    G = 1
    KG = 1000 * G
    LB = 453.59237 * G

    __path__ = ()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("build123d", *args, **kwargs)

    @property
    def __all__(self) -> Sequence[str]:
        return list(set(dir(self)) - set(dir(MagicMock())))


@contextmanager
def exit_mock() -> Iterator[None]:
    @dataclass
    class ExitError(Exception):
        code: int | str

    def stub(code: str | int) -> None:
        raise ExitError(code)

    with patch.object(sys, "exit", stub), patch.object(os, "_exit", stub):
        try:
            yield
        except ExitError as e:
            raise SystemExit(e.code) from e


@dataclass
class PatchModule:
    name: str
    original: ModuleType | None = field(default=None, init=False)
    replacement: ModuleType = field(default_factory=MagicMock)
    auto: bool = True
    started: bool = field(default=False, init=False)
    recursive: bool = False
    submodules: list[str] = field(default_factory=list, init=False)

    def __enter__(self) -> Self:
        if self.auto:
            self.start()
        return self

    @cached_property
    def module_finder(self) -> importlib.abc.MetaPathFinder:
        @dataclass
        class MockFinder(importlib.abc.MetaPathFinder):
            name: str

            class MockLoader(importlib.abc.Loader):
                submodules = self.submodules

                def create_module(
                    self, spec: importlib.machinery.ModuleSpec
                ) -> ModuleType:
                    self.submodules.append(spec.name)
                    return MagicMock(name=spec.name)

                def exec_module(self, module: ModuleType) -> None:
                    pass

            def find_spec(
                self,
                fullname: str,
                _path: Sequence[str] | None,
                _target: ModuleType | None = None,
            ) -> importlib.machinery.ModuleSpec | None:
                if fullname == self.name or fullname.startswith(
                    self.name + "."
                ):
                    return importlib.util.spec_from_loader(
                        fullname, self.MockLoader(), is_package=True
                    )
                return None

        return MockFinder(name=self.name)

    def start(self) -> None:

        if not self.started:
            self.original = sys.modules.get(self.name)
            sys.modules[self.name] = self.replacement
            if self.recursive:
                sys.meta_path.insert(0, self.module_finder)
        self.started = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        if not self.started:
            return
        if self.recursive:
            for submodule in self.submodules:
                sys.modules.pop(submodule, None)
            sys.meta_path.pop(0)
        if self.original:
            sys.modules[self.name] = self.original
        else:
            del sys.modules[self.name]
