"""Parameter system serializer and schema tests."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, Protocol

import pytest

from bdbox.model.field_factories import Float, Int
from bdbox.model.parameters import Params
from bdbox.model.preset import Preset
from bdbox.model.state import model_state
from bdbox.runner.harness import ModelHarness
from bdbox.runner.runner import ModelRunner
from bdbox.serializer import serializer
from tests.utils import Models

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from syrupy import SnapshotAssertion


class Runner(Protocol):
    def __init__(
        self, model_argv: Sequence[Path | str] | Path | str = ()
    ) -> None: ...


class SchemaModels:
    @classmethod
    def complex_model(cls, model_base: type[Params]) -> type[Params]:
        @dataclass
        class Point:
            x: float = 0.0
            y: float = 0.0

        class Color(Enum):
            RED = "red"
            BLUE = "blue"
            PURPLE = "purple"

        @dataclass
        class NestedNestedT:
            point: Point = field(default_factory=Point)
            color: Color = Color.PURPLE
            maybe_color: Color | None = Color.RED
            kinda_color: Color | int | None = Color.BLUE
            size: None | Literal["small", "medium", "large", 1] = "small"
            thing: None | str | float | Literal[1, 2] = 4.4
            other_thing: int | str = 5

        @dataclass
        class NestedT:
            point: Point = field(default_factory=Point)
            nested: NestedNestedT = field(default_factory=NestedNestedT)
            several: Sequence[NestedNestedT] = field(default_factory=list)

        class T(model_base):  # ty: ignore[unsupported-base]
            count: int = 0
            more_count = Int(6, min=2, max=10, step=2)
            nested: NestedT = field(
                default_factory=lambda: NestedT(Point(30.0, 40.0))
            )
            point: Point = field(default_factory=lambda: Point(10.0, 20.0))
            top_several: Sequence[NestedNestedT] = field(default_factory=list)

        return T


JsonSnapshot = Callable[[Any], None]


@pytest.fixture
def json_snapshot(snapshot: SnapshotAssertion) -> JsonSnapshot:
    def _assert(value: Any) -> None:
        assert json.dumps(value, indent=4) == snapshot

    return _assert


@pytest.fixture(
    params=[
        pytest.param(Models.MODEL_EXPORT, id="Model"),
        pytest.param(Models.PARAMS_EXPORT, id="Params"),
        pytest.param(Models.MONO_MODEL, id="mono_model"),
        pytest.param(Models.MONO_PARAMS, id="mono_params"),
        pytest.param(Models.MONO_PLAIN, id="mono_plain"),
        pytest.param(f"{Models.MONO_PARAMS}:P", id="mono_params_class"),
        pytest.param(f"{Models.MONO_MODEL}:MyModel", id="mono_model_class"),
    ]
)
def model(request: pytest.FixtureRequest) -> Path:
    return request.param


@pytest.fixture(
    params=(
        pytest.param(ModelHarness, id="harness"),
        pytest.param(ModelRunner, id="runner"),
    )
)
def runner(request: pytest.FixtureRequest) -> Runner:
    return request.param


def test_schema_fields(model_base: type[Params]) -> None:
    class T(Params):
        width = Float(10.0, min=5.0, max=100.0)
        count = Int(3, min=1, max=10)

    assert serializer.json_schema(T) == {
        "properties": {
            "count": {
                "default": 3,
                "maximum": 10,
                "minimum": 1,
                "type": "number",
                "x-format": "range",
            },
            "width": {
                "default": 10.0,
                "maximum": 100.0,
                "minimum": 5.0,
                "type": "number",
                "x-format": "range",
            },
        },
        "type": "object",
        "required": ["count", "width"],
        "x-presets": [],
    }


def test_schema_with_presets(model_base: type[Params]) -> None:
    class T(model_base):  # ty: ignore[unsupported-base]
        width = Float(10.0, min=5.0, max=100.0)
        presets = (
            Preset("small", width=5.0),
            Preset("large", description="Full size", width=80.0),
        )

    schema = serializer.json_schema(T)
    assert schema == {
        "properties": {
            "width": {
                "default": 10.0,
                "maximum": 100.0,
                "minimum": 5.0,
                "type": "number",
                "x-format": "range",
            },
        },
        "type": "object",
        "required": ["width"],
        "x-presets": [
            {"name": "small", "values": {"width": 5.0}},
            {
                "description": "Full size",
                "name": "large",
                "values": {"width": 80.0},
            },
        ],
    }


def test_schema_empty(model_base: type[Params]) -> None:
    class T(model_base):  # ty: ignore[unsupported-base]
        pass

    assert serializer.json_schema(T) == {
        "type": "object",
        "properties": {},
        "required": [],
        "x-presets": [],
    }


def test_schema_complex(
    model_base: type[Params], json_snapshot: JsonSnapshot
) -> None:
    T = SchemaModels.complex_model(model_base)  # noqa: N806
    json_snapshot(serializer.json_schema(T))


def test_unstructure_complex(
    model_base: type[Params], json_snapshot: JsonSnapshot
) -> None:
    T = SchemaModels.complex_model(model_base)  # noqa: N806
    json_snapshot(serializer.unstructure(T()))


def test_model_schema_cached_at_runtime(
    runner: type[Runner],
    model: Path,
    json_snapshot: JsonSnapshot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if runner is ModelHarness:
        monkeypatch.setattr(sys, "argv", ["bdbox", str(model)])
    assert model_state.schema == {}
    runner(model)()
    json_snapshot(model_state.schema)
