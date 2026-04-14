"""Model file invocation tests."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Sequence

    from syrupy.assertion import SnapshotAssertion

MODELS_DIR = Path(__file__).parent / "models"

MIXED_MODEL_THEN_PARAMS = MODELS_DIR / "mixed_model_then_params.py"
MIXED_PARAMS_THEN_MODEL = MODELS_DIR / "mixed_params_then_model.py"
MODEL_CLASS = MODELS_DIR / "model_class.py"
MODEL_CLASS_BLANK = MODELS_DIR / "model_class_blank.py"
MODEL_CLASS_MULTIPLE = MODELS_DIR / "model_class_multiple.py"
MODEL_CLASS_SUBCLASS = MODELS_DIR / "model_class_subclass.py"
PARAMS_CLASS = MODELS_DIR / "params_class.py"
PARAMS_CLASS_BLANK = MODELS_DIR / "params_class_blank.py"
PARAMS_CLASS_MULTIPLE_PARAMS = MODELS_DIR / "params_class_multiple_params.py"
PARAMS_CLASS_INSTANCE = MODELS_DIR / "params_class_instance.py"


def _run(cmd: Sequence[Any], test_mode: str = "", **kwargs: Any) -> str:
    kwargs.setdefault("env", os.environ | {"BDBOX_TEST_MODEL_MODE": test_mode})
    kwargs.setdefault("text", True)
    kwargs.setdefault("stdout", subprocess.PIPE)
    kwargs.setdefault("stderr", subprocess.STDOUT)
    result = subprocess.run(  # noqa: S603
        [sys.executable, *[str(c) for c in cmd]], check=True, **kwargs
    )
    assert result.returncode == 0
    return result.stdout.strip()


def _run_raises(
    cmd: Sequence[Any], match: str | None
) -> subprocess.CalledProcessError:
    with pytest.raises(
        subprocess.CalledProcessError, match="returned non-zero exit status"
    ) as ee:
        _run(cmd)
    assert ee.value.returncode != 0
    if match is not None:
        assert match in (ee.value.output or "")
    return ee.value


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


def test_mixed_model_then_params_raises() -> None:
    _run_raises(
        [MIXED_MODEL_THEN_PARAMS],
        "Cannot use Params subclass with an existing Model subclass",
    )


def test_mixed_params_then_model_raises() -> None:
    _run_raises([MIXED_PARAMS_THEN_MODEL], "Cannot define Model subclass")


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param(["--preset", "small", "--width", "25.4"], id="render"),
    ],
)
def test_model(
    snapshot: SnapshotAssertion,
    model_class_test_mode: str,
    args: Sequence[str],
) -> None:
    result = _run([MODEL_CLASS, *args], model_class_test_mode)
    assert result == snapshot


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param([], id="render"),
    ],
)
def test_model_blank(
    snapshot: SnapshotAssertion,
    model_class_test_mode: str,
    args: Sequence[str],
) -> None:
    result = _run([MODEL_CLASS_BLANK, *args], model_class_test_mode)
    assert result == snapshot


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param(["--width", "25.4"], id="render"),
    ],
)
def test_model_multiple(
    snapshot: SnapshotAssertion,
    model_class_test_mode: str,
    args: Sequence[str],
) -> None:
    result = _run([MODEL_CLASS_MULTIPLE, *args], model_class_test_mode)
    assert result == snapshot


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param(["--width", "25.4"], id="render"),
    ],
)
def test_model_subclass(
    snapshot: SnapshotAssertion,
    model_class_test_mode: str,
    args: Sequence[str],
) -> None:
    result = _run([MODEL_CLASS_SUBCLASS, *args], model_class_test_mode)
    assert result == snapshot


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param(["--preset", "small", "--width", "25.4"], id="render"),
    ],
)
def test_params_class(
    snapshot: SnapshotAssertion,
    params_class_test_mode: str,
    args: Sequence[str],
) -> None:
    result = _run([PARAMS_CLASS, *args], params_class_test_mode)
    assert result == snapshot


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(["--help"], id="help"),
        pytest.param([], id="render"),
    ],
)
def test_params_class_blank(
    snapshot: SnapshotAssertion,
    params_class_test_mode: str,
    args: Sequence[str],
) -> None:
    result = _run([PARAMS_CLASS_BLANK, *args], params_class_test_mode)
    assert result == snapshot


def test_params_class_multiple_params_raises() -> None:
    _run_raises(
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
def test_params_class_instance(
    snapshot: SnapshotAssertion, args: Sequence[str]
) -> None:
    result = _run([PARAMS_CLASS_INSTANCE, *args])
    assert result == snapshot
