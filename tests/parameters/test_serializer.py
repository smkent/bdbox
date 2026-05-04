"""Parameter system serializer and schema tests."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

import pytest

from bdbox.parameters.field_factories import Float, Int
from bdbox.parameters.parameters import Params
from bdbox.parameters.preset import Preset
from bdbox.parameters.serializer import Serializer

if TYPE_CHECKING:
    from collections.abc import Sequence

    from syrupy import SnapshotAssertion


class Models:
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


def test_schema_fields(model_base: type[Params]) -> None:
    class T(Params):
        width = Float(10.0, min=5.0, max=100.0)
        count = Int(3, min=1, max=10)

    assert T.schema() == {
        "properties": {
            "count": {
                "name": "count",
                "step": None,
                "description": None,
                "default": 3,
                "max": 10,
                "min": 1,
                "type": "number",
            },
            "width": {
                "name": "width",
                "step": None,
                "description": None,
                "default": 10.0,
                "max": 100.0,
                "min": 5.0,
                "type": "number",
            },
        },
        "type": "object",
        "x-presets": [],
    }


def test_schema_with_presets(model_base: type[Params]) -> None:
    class T(model_base):  # ty: ignore[unsupported-base]
        width = Float(10.0, min=5.0, max=100.0)
        presets = (
            Preset("small", width=5.0),
            Preset("large", description="Full size", width=80.0),
        )

    schema = T.schema()
    assert schema == {
        "properties": {
            "width": {
                "name": "width",
                "step": None,
                "description": None,
                "default": 10.0,
                "max": 100.0,
                "min": 5.0,
                "type": "number",
            },
        },
        "type": "object",
        "x-presets": [
            {
                "description": None,
                "name": "small",
                "values": {
                    "width": 5.0,
                },
            },
            {
                "description": "Full size",
                "name": "large",
                "values": {
                    "width": 80.0,
                },
            },
        ],
    }


def test_schema_empty(model_base: type[Params]) -> None:
    class T(model_base):  # ty: ignore[unsupported-base]
        pass

    assert T.schema() == {"type": "object", "properties": {}, "x-presets": []}


def test_schema_complex(
    model_base: type[Params], json_snapshot: JsonSnapshot
) -> None:
    T = Models.complex_model(model_base)  # noqa: N806
    json_snapshot(T.schema())


def test_unstructure_complex(
    model_base: type[Params], json_snapshot: JsonSnapshot
) -> None:
    T = Models.complex_model(model_base)  # noqa: N806
    json_snapshot(Serializer().unstructure(T()))
