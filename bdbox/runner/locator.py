from __future__ import annotations

import importlib.machinery
import re
import sys
from contextlib import contextmanager, suppress
from dataclasses import InitVar, dataclass, field
from functools import cached_property
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from bdbox.errors import InternalError
from bdbox.model.info import ModelInfo

from .env import EnvLocator

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence


@dataclass
class ModelLocator:
    model: ModelInfo = field(default_factory=ModelInfo, init=False)
    env_search: ClassVar[bool] = False
    model_argv: InitVar[Sequence[Path | str] | Path | str] = ()

    def __post_init__(
        self, model_argv: Sequence[Path | str] | Path | str
    ) -> None:
        self.model.argv = self._setup_argv(model_argv)
        self._model_path_from_argv()

    def _setup_argv(
        self, model_argv: Sequence[Path | str] | Path | str
    ) -> list[str]:
        return (
            [str(model_argv)]
            if isinstance(model_argv, (Path, str))
            else [str(v) for v in model_argv]
        )

    @cached_property
    def model_base_dir(self) -> Path:
        if not self.model.path:
            raise InternalError("Model path missing")
        base_dir = self.model.path.parent
        if self.model.module_name:
            for _ in range(self.model.module_name.count(".")):
                if not ((parent := base_dir.parent) / "__init__.py").exists():
                    break
                base_dir = parent
        return base_dir

    @contextmanager
    def module_cleanup(self, name: str | None = None) -> Iterator[None]:
        before_keys = set(sys.modules.keys())
        yield
        after_keys = sorted(set(sys.modules.keys()) - before_keys)
        if not after_keys:
            return
        if name:
            base_name = name.split(".", maxsplit=1)[0]
            after_keys = [
                ak
                for ak in after_keys
                if ak == base_name or ak.startswith(f"{base_name}.")
            ]
        extension_modules = {
            ak
            for ak in after_keys
            if isinstance(
                getattr(sys.modules.get(ak, None), "__loader__", None),
                importlib.machinery.ExtensionFileLoader,
            )
        }
        extension_prefixes = tuple(f"{p}." for p in extension_modules)
        after_keys = [
            ak
            for ak in after_keys
            if not (
                ak in extension_modules or ak.startswith(extension_prefixes)
            )
        ]
        for ak in after_keys:
            sys.modules.pop(ak, None)

    def _model_arg_and_attr(self, name: str) -> tuple[str, str | None]:
        if ":" not in name:
            return name, None
        name, attr = name.split(":", maxsplit=1)
        return name, attr

    def _file_from_module(self, name: str) -> str | None:
        with self.module_cleanup(name), suppress(ModuleNotFoundError):
            mod_name, mod_attr = self._model_arg_and_attr(name)
            if self.env_search:
                EnvLocator(target_module=mod_name).ensure_env()
            if (spec := find_spec(mod_name)) and spec.origin:
                self.model.module_name = mod_name
                self.model.class_name = mod_attr or None
                return spec.origin
        return None

    def _model_path_from_argv(self) -> None:
        for arg in self.model.argv:
            if not arg.startswith("-"):
                file_name, file_attr = self._model_arg_and_attr(arg)
                if Path(file_name).suffix != ".py":
                    continue
                self.model.argv.pop(self.model.argv.index(arg))
                if self.env_search:
                    EnvLocator(file_name).ensure_env()
                self.model.class_name = file_attr or None
                self.model.arg = file_name
                return
        for arg in self.model.argv:
            if (
                arg.startswith(".")
                or not re.match(r"^[A-Za-z0-9_.:]+$", arg)
                or Path(arg).is_file()
            ):
                continue
            if arg_file := self._file_from_module(arg):
                self.model.argv.pop(self.model.argv.index(arg))
                self.model.arg = arg_file
