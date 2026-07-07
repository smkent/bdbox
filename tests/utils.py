from __future__ import annotations

import sys
import threading
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from bdbox import examples
from bdbox.__main__ import main
from bdbox.errors import RunError

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence
    from types import TracebackType


@dataclass
class ExecMain:
    monkeypatch: pytest.MonkeyPatch

    def __call__(self, *args: str) -> None:
        self.monkeypatch.setattr(sys, "argv", ["bdbox", *args])
        main()


class Examples:
    DIR = Path(examples.__file__).parent

    BOX_DEMO = DIR / "demo.py"


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

    @dataclass
    class Builder:
        shape: MockBuild123d.Shape | None = None

        @property
        def _obj_name(self) -> str:
            return "shape"

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

    class Config(ModuleType):
        class Camera(Enum):
            KEEP = "keep"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__("config", *args, **kwargs)

        def reset_defaults(self, *args: Any, **kwargs: Any) -> None:
            pass

        def set_defaults(self, *args: Any, **kwargs: Any) -> None:
            pass

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("ocp_vscode", *args, **kwargs)

    def show(*args: Any, **kwargs: Any) -> None:
        pass

    comms = Comms()
    config = Config()


@dataclass
class ThreadExceptions:
    exceptions: list[
        tuple[type[BaseException], BaseException, TracebackType | None]
    ] = field(default_factory=list, init=False)

    class MissingExceptionError(Exception):
        pass

    @contextmanager
    def catch(self) -> Iterator[None]:
        def excepthook(args: threading.ExceptHookArgs) -> None:
            self.exceptions.append(
                (
                    args.exc_type,
                    args.exc_value or Exception("Exception value missing"),
                    args.exc_traceback,
                )
            )

        with patch.object(threading, "excepthook", excepthook):
            yield
        for exc_info in self.exceptions:
            raise exc_info[1].with_traceback(exc_info[2])
        assert not self.exceptions

    @contextmanager
    def raises(
        self, exc_type: type[BaseException] | tuple[type[BaseException], ...]
    ) -> Iterator[None]:
        context_exceptions = []
        with patch.object(self, "exceptions", context_exceptions):
            yield
        if not context_exceptions:
            raise self.MissingExceptionError(exc_type)
        for _, exception, _ in context_exceptions:
            if not isinstance(exception, exc_type):
                raise exception


@dataclass
class RaisesRunError:
    expected_exception: type[BaseException]
    match: str | None = field(default=None, kw_only=True)

    stack: ExitStack = field(default_factory=ExitStack, init=False, repr=False)
    exc_info: pytest.ExceptionInfo | None = field(default=None, init=False)

    def __enter__(self) -> Self:
        self.exc_info = self.stack.enter_context(
            pytest.raises(RunError, match=self.match)
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        result = self.stack.__exit__(exc_type, exc_val, exc_tb)
        assert self.exc_info
        assert (
            type(self.exc_info.value.exception) is self.expected_exception
        ), f"Raised RunError did not contain {self.expected_exception}"
        return result
