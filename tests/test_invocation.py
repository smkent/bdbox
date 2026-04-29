"""Model file invocation tests."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest

from .utils import Models

if TYPE_CHECKING:
    from collections.abc import Sequence

    from syrupy.assertion import SnapshotAssertion

    from .utils import DisallowCallable

MIXED_MODEL_THEN_PARAMS = Models.DIR / "mixed_model_then_params.py"
MIXED_PARAMS_THEN_MODEL = Models.DIR / "mixed_params_then_model.py"
MODEL_CLASS = Models.DIR / "model_class.py"
MODEL_CLASS_BLANK = Models.DIR / "model_class_blank.py"
MODEL_CLASS_MULTIPLE = Models.DIR / "model_class_multiple.py"
MODEL_CLASS_SUBCLASS = Models.DIR / "model_class_subclass.py"
PARAMS_CLASS = Models.DIR / "params_class.py"
PARAMS_CLASS_BLANK = Models.DIR / "params_class_blank.py"
PARAMS_CLASS_MULTIPLE_PARAMS = Models.DIR / "params_class_multiple_params.py"
PARAMS_CLASS_INSTANCE = Models.DIR / "params_class_instance.py"
MODEL_MODULE = "mod_model"
PARAMS_MODULE = "mod_params"


@dataclass
class Runner:
    disallow_subprocess: DisallowCallable
    snapshot: SnapshotAssertion

    def __call__(
        self, cmd: Sequence[Any], test_mode: str = "", **kwargs: Any
    ) -> str:
        kwargs.setdefault(
            "env", os.environ | {"BDBOX_TEST_MODEL_MODE": test_mode}
        )
        kwargs.setdefault("text", True)
        kwargs.setdefault("stdout", subprocess.PIPE)
        kwargs.setdefault("stderr", subprocess.STDOUT)
        with self.disallow_subprocess.pause():
            result = subprocess.run(  # noqa: S603
                [sys.executable, *[str(c) for c in cmd]], check=True, **kwargs
            )
        assert result.returncode == 0
        return result.stdout.strip()

    def match_snapshot(
        self, cmd: Sequence[Any], *args: Any, **kwargs: Any
    ) -> None:
        assert self(cmd, *args, **kwargs) == self.snapshot

    def raises(
        self, cmd: Sequence[Any], match: str | None
    ) -> subprocess.CalledProcessError:
        with pytest.raises(
            subprocess.CalledProcessError,
            match="returned non-zero exit status",
        ) as ee:
            self(cmd)
        assert ee.value.returncode != 0
        if match is not None:
            assert match in (ee.value.output or "")
        return ee.value


@pytest.fixture
def runner(
    disallow_subprocess: DisallowCallable, snapshot: SnapshotAssertion
) -> Runner:
    return Runner(disallow_subprocess, snapshot)


@pytest.fixture(
    params=(
        pytest.param("", id="normal"),
        pytest.param("run", id="run"),
    )
)
def model_class_test_mode(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture(
    params=(
        pytest.param("", id="normal"),
        pytest.param("show", id="show"),
        pytest.param("show_noparams", id="noparams"),
    )
)
def params_class_test_mode(request: pytest.FixtureRequest) -> str:
    return request.param


def test_mixed_model_then_params_raises(runner: Runner) -> None:
    runner.raises(
        [MIXED_MODEL_THEN_PARAMS],
        "Cannot use Params subclass with an existing Model subclass",
    )


def test_mixed_params_then_model_raises(runner: Runner) -> None:
    runner.raises([MIXED_PARAMS_THEN_MODEL], "Cannot define Model subclass")


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param(
            ["--sub.a", "1", "--preset", "small", "--width", "25.4"],
            id="render",
        ),
    ],
)
def test_model(
    runner: Runner, model_class_test_mode: str, args: Sequence[str]
) -> None:
    runner.match_snapshot([MODEL_CLASS, *args], model_class_test_mode)


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param([], id="render"),
    ],
)
def test_model_blank(
    runner: Runner, model_class_test_mode: str, args: Sequence[str]
) -> None:
    runner.match_snapshot([MODEL_CLASS_BLANK, *args], model_class_test_mode)


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param(["--width", "25.4"], id="render"),
    ],
)
def test_model_multiple(
    runner: Runner, model_class_test_mode: str, args: Sequence[str]
) -> None:
    runner.match_snapshot([MODEL_CLASS_MULTIPLE, *args], model_class_test_mode)


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param(["--width", "25.4"], id="render"),
    ],
)
def test_model_subclass(
    runner: Runner, model_class_test_mode: str, args: Sequence[str]
) -> None:
    runner.match_snapshot([MODEL_CLASS_SUBCLASS, *args], model_class_test_mode)


@pytest.mark.parametrize(
    "args",
    [pytest.param(["--help"], id="help"), pytest.param([], id="render")],
)
@pytest.mark.parametrize(
    "sub_module",
    [pytest.param("", id="no_submodule"), pytest.param(".model", id="model")],
)
@pytest.mark.parametrize("module", [MODEL_MODULE, PARAMS_MODULE])
def test_module_models(
    runner: Runner, module: str, sub_module: str, args: Sequence[str]
) -> None:
    runner.match_snapshot(
        ["-m", "bdbox", f"tests.models.{module}{sub_module}", *args]
    )


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param(
            ["--sub.a", "1", "--preset", "small", "--width", "25.4"],
            id="render",
        ),
    ],
)
def test_params_class(
    runner: Runner, params_class_test_mode: str, args: Sequence[str]
) -> None:
    runner.match_snapshot([PARAMS_CLASS, *args], params_class_test_mode)


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param([], id="render"),
    ],
)
def test_params_class_blank(
    runner: Runner, params_class_test_mode: str, args: Sequence[str]
) -> None:
    runner.match_snapshot([PARAMS_CLASS_BLANK, *args], params_class_test_mode)


def test_params_class_multiple_params_raises(runner: Runner) -> None:
    runner.raises(
        [PARAMS_CLASS_MULTIPLE_PARAMS],
        "a Params subclass is already defined in this script",
    )


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param(
            ["--preset", "small", "--width", "25.4", "--height", "30"],
            id="render",
        ),
    ],
)
def test_params_class_instance(runner: Runner, args: Sequence[str]) -> None:
    runner.match_snapshot([PARAMS_CLASS_INSTANCE, *args])
