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
    from collections.abc import Callable, Iterator

    import pytest

MODELS_DIR = Path(__file__).parent / "models"


class Models:
    DIR = Path(__file__).parent / "models"

    MODEL_EXPORT = DIR / "model_export.py"
    PARAMS_EXPORT = DIR / "params_export.py"
    PLAIN_EXPORT = DIR / "plain_export.py"


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
