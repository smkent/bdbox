from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from types import ModuleType
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

from bdbox.model import Model
from bdbox.parameters.parameters import Params

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from pathlib import Path

AtExitHook = Callable[..., Any]


class AtExit(ModuleType):
    hooks: list[tuple[AtExitHook, tuple[Any, dict[str, Any]]]]

    @classmethod
    @contextmanager
    def mock(cls) -> Iterator[Self]:
        mock_atexit = AtExit()
        with (
            patch(f"{Model.__module__}.atexit", mock_atexit),
            patch(f"{Params.__module__}.atexit", mock_atexit),
        ):
            yield mock_atexit  # ty: ignore[invalid-yield]
            mock_atexit.run_hooks()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("atexit", *args, **kwargs)
        self.hooks = []

    def register(
        self, func: AtExitHook, *args: Any, **kwargs: Any
    ) -> AtExitHook:
        self.hooks.append((func, (args, kwargs)))
        return func

    def unregister(self, func: AtExitHook) -> None:
        self.hooks = [
            (f, args_kwargs) for f, args_kwargs in self.hooks if func != f
        ]

    def run_hooks(self) -> None:
        for func, (args, kwargs) in reversed(self.hooks):
            func(*args, **kwargs)


class MainModule(ModuleType):
    def __init__(
        self,
        filename: str | Path | None = None,
        module_name: str | None = None,
    ) -> None:
        super().__init__("__main__")
        self.__filename__ = str(filename) if filename else None
        self.__module_name__ = module_name
