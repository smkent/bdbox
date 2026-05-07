from __future__ import annotations

import re
import sys
from contextlib import contextmanager, suppress
from dataclasses import InitVar, dataclass, field
from functools import cached_property
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from bdbox.errors import InternalError

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


@dataclass
class ModelLocator:
    clean_modules: ClassVar[bool] = False
    model_argv: InitVar[Sequence[Path | str] | Path | str] = ()
    model_path: Path | None = field(default=None, init=False)
    model_module: str | None = field(default=None, init=False)
    model_filename: str | None = field(default=None, init=False)
    model_class_name: str | None = field(default=None, init=False)
    argv: list[str] = field(default_factory=list, init=False)

    def __post_init__(
        self, model_argv: Sequence[Path | str] | Path | str
    ) -> None:
        self.argv = (
            [str(model_argv)]
            if isinstance(model_argv, (Path, str))
            else [str(v) for v in model_argv]
        )
        model_file = self._model_path_from_argv()
        if model_file:
            self.model_path = Path(model_file).resolve()
            self.model_filename = str(model_file)

    @cached_property
    def model_base_dir(self) -> Path:
        if self.model_module:
            base_module = self.model_module.split(".", 1)[0]
            if file := getattr(sys.modules.get(base_module), "__file__", None):
                return Path(file).parent
        if not self.model_path:
            raise InternalError("Model path missing")
        return self.model_path.parent

    @contextmanager
    def module_cleanup(self, name: str | None = None) -> Iterator[None]:
        name = name or self.model_module
        if not self.clean_modules or not name:
            yield
            if self.model_module and self.model_module in sys.modules:
                sys.modules.pop(self.model_module)
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
            if ":" not in name:
                name += ":"
            mod_name, mod_attr = name.split(":", maxsplit=1)
            if (spec := find_spec(mod_name)) and spec.origin:
                self.model_module = mod_name
                self.model_class_name = mod_attr or None
                return spec.origin
        return None

    def _model_path_from_argv(self) -> str | None:
        for arg in self.argv:
            if not arg.startswith("-") and Path(arg).suffix == ".py":
                self.argv.pop(self.argv.index(arg))
                return arg
        for arg in self.argv:
            if not re.match(r"^[A-Za-z0-9_.:]+$", arg) or Path(arg).is_file():
                continue
            if arg_file := self._file_from_module(arg):
                self.argv.pop(self.argv.index(arg))
                return arg_file
        return None
