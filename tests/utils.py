from __future__ import annotations

import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

    import pytest


class Models:
    DIR = Path(__file__).parent / "models"

    MIXED_MODEL_THEN_PARAMS = DIR / "mixed_model_then_params.py"
    MIXED_PARAMS_THEN_MODEL = DIR / "mixed_params_then_model.py"
    MODEL_CLASS = DIR / "model_class.py"
    MODEL_CLASS_BLANK = DIR / "model_class_blank.py"
    MODEL_CLASS_MULTIPLE = DIR / "model_class_multiple.py"
    MODEL_CLASS_SUBCLASS = DIR / "model_class_subclass.py"
    PARAMS_CLASS = DIR / "params_class.py"
    PARAMS_CLASS_BLANK = DIR / "params_class_blank.py"
    PARAMS_CLASS_MULTIPLE_PARAMS = DIR / "params_class_multiple_params.py"
    PARAMS_CLASS_INSTANCE = DIR / "params_class_instance.py"

    MODEL_EXPORT = DIR / "model_export.py"
    PARAMS_EXPORT = DIR / "params_export.py"
    PLAIN_EXPORT = DIR / "plain_export.py"
    MOD_MODEL = "tests.models.mod_model"
    MOD_PARAMS = "tests.models.mod_params"
    MOD_PLAIN = "tests.models.mod_plain"
    MONO_MODEL = "tests.models.mono_model.models.model"
    MONO_PARAMS = "tests.models.mono_params.models.model"
    MONO_PLAIN = "tests.models.mono_plain.models.model"


@dataclass
class DisallowCallable:
    request: pytest.FixtureRequest
    obj: object
    attr: str
    original: Callable[..., Any] = field(init=False)
    enabled: bool = field(default=False, init=False)
    mock_attr: MagicMock | None = field(default=None, init=False)

    @dataclass
    class DisallowedError(Exception):
        mock: DisallowCallable

        def __str__(self) -> str:
            fn = self.mock.original
            name = f"{fn.__module__}." + (
                getattr(fn, "__qualname__", None)
                or getattr(fn, "__name__", "(unknown)")
            )
            return f"`{name}` disallowed via {self.mock.request.fixturename}"

    def __post_init__(self) -> None:
        self.original = getattr(self.obj, self.attr)

    @contextmanager
    def __call__(self) -> Iterator[Self]:

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if self.enabled:
                return self.original(*args, **kwargs)
            raise self.DisallowedError(self)

        with patch.object(
            self.obj, self.attr, autospec=True, side_effect=wrapper
        ) as mock_attr:
            self.mock_attr = mock_attr
            yield self

    @contextmanager
    def pause(self) -> Iterator[None]:
        if self.mock_attr:
            with patch.object(self.obj, self.attr, self.original):
                yield
            self.mock_attr.assert_not_called()


class MockBuild123d(ModuleType):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("build123d", *args, **kwargs)

    class Shape:
        pass

    class ShapeList(list):
        pass

    @dataclass
    class Compound(Shape):
        children: Sequence[MockBuild123d.Shape] = field(default_factory=tuple)
        label: str = ""

        def show_topology(self, limit_class: str | None = None) -> str:
            return ""


class MockOcpVscode(ModuleType):
    class Comms(ModuleType):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__("comms", *args, **kwargs)

        def set_port(self, port: int | None) -> None:
            pass

        def send_command(self, cmd: str) -> None:
            pass

        CMD_PORT = 3939

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("ocp_vscode", *args, **kwargs)

    def show(*args: Any, **kwargs: Any) -> None:
        pass

    comms = Comms()
