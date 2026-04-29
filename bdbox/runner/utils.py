from __future__ import annotations

import re
import sys
from contextlib import contextmanager, suppress
from dataclasses import InitVar, dataclass, field
from functools import cached_property
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from bdbox.geometry import reset_geometry
from bdbox.model import Model
from bdbox.parameters.parameters import Params

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from types import ModuleType, TracebackType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


def reset_bdbox() -> None:
    """Reset all bdbox module-level state for runners or tests."""
    reset_geometry()
    for params_class in [Params, Model]:
        params_class._main_info.__init__()  # noqa: SLF001


@dataclass
class ModelLocator:
    clean_modules: ClassVar[bool] = False
    model_argv: InitVar[Sequence[Path | str] | Path | str] = ()
    model_path: Path = field(init=False)
    model_module: str | None = field(default=None, init=False)
    model_filename: str = field(init=False)
    argv: list[str] = field(default_factory=list, init=False)

    def __post_init__(
        self, model_argv: Sequence[Path | str] | Path | str
    ) -> None:
        self.argv = (
            [str(model_argv)]
            if isinstance(model_argv, (Path, str))
            else [str(v) for v in model_argv]
        )
        (model_file, model_module) = self._model_path_from_argv()
        if model_file:
            self.model_path = Path(model_file).resolve()
            self.model_filename = str(model_file)
        if model_module:
            self.model_module = model_module

    @cached_property
    def model_base_dir(self) -> Path:
        if self.model_module:
            base_module = self.model_module.split(".", 1)[0]
            if file := getattr(sys.modules.get(base_module), "__file__", None):
                return Path(file).parent
        return self.model_path.parent

    @contextmanager
    def module_cleanup(self, name: str | None = None) -> Iterator[None]:
        if not (self.clean_modules and (name := name or self.model_module)):
            yield
            return
        before_keys = set(sys.modules.keys())
        yield
        after_keys = set(sys.modules.keys()) - before_keys
        base_name = name.split(".", maxsplit=1)[0]
        for ak in sorted(after_keys):
            if ak == base_name or ak.startswith(f"{base_name}."):
                sys.modules.pop(ak)

    def _file_from_module(self, name: str) -> str | None:
        with self.module_cleanup(name), suppress(ModuleNotFoundError):
            if (spec := find_spec(name)) and spec.origin:
                return spec.origin
        return None

    def _model_path_from_argv(self) -> tuple[str | None, str | None]:
        for arg in self.argv:
            if not arg.startswith("-") and Path(arg).suffix == ".py":
                self.argv.pop(self.argv.index(arg))
                return arg, None
        for arg in self.argv:
            if not re.match(r"^[A-Za-z0-9_.]+$", arg) or Path(arg).is_file():
                continue
            if arg_file := self._file_from_module(arg):
                self.argv.pop(self.argv.index(arg))
                return arg_file, arg
        return None, None


@dataclass
class PatchModule:
    name: str
    original: ModuleType | None = field(default=None, init=False)
    replacement: ModuleType
    auto: bool = True
    started: bool = field(default=False, init=False)

    def __enter__(self) -> Self:
        if self.auto:
            self.start()
        return self

    def start(self) -> None:
        if not self.started:
            self.original = sys.modules.get(self.name)
            sys.modules[self.name] = self.replacement
        self.started = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        if not self.started:
            return
        if self.original:
            sys.modules[self.name] = self.original
        else:
            del sys.modules[self.name]
