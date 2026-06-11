from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from types import ModuleType
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

from .utils import PatchModule

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from pathlib import Path

AtExitHook = Callable[..., Any]


class AtExit(ModuleType):
    SEARCH_MODULES = ("bdbox.model.model", "bdbox.model.parameters")

    hooks: list[tuple[AtExitHook, tuple[Any, dict[str, Any]]]]

    @classmethod
    @contextmanager
    def mock(cls) -> Iterator[Self]:
        builtin_atexit = sys.modules.get("atexit")
        mock_atexit = cls()
        with ExitStack() as mock_stack, PatchModule("atexit", mock_atexit):
            for module, attr_name in [
                (mod, attr_name)
                for mod_name in cls.SEARCH_MODULES
                if isinstance((mod := sys.modules.get(mod_name)), ModuleType)
                for attr_name, attr_val in list(vars(mod).items())
                if attr_val is builtin_atexit
            ]:
                mock_stack.enter_context(
                    patch.object(module, attr_name, mock_atexit)
                )
            yield mock_atexit
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
