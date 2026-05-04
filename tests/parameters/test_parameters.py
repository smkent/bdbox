"""Parameters system tests."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

import pytest

from bdbox.errors import ParamsError, ParamValidationError
from bdbox.parameters.field_factories import Float, Int, Str
from bdbox.parameters.parameters import Params
from bdbox.parameters.preset import Preset
from bdbox.parameters.state import run_state

if TYPE_CHECKING:
    from collections.abc import Sequence


def test_params_empty() -> None:
    class P(Params):
        pass

    params_fields = tuple(f for f in fields(P) if f.name != "preset")
    assert params_fields == ()
    assert P.presets == ()


def test_params_value_access() -> None:
    class P(Params):
        width = Float(default=10.0, min=5.0)
        length = 15.0
        count = Int(default=3)

    assert P.width == 10.0
    assert P.length == 15.0
    assert P.count == 3


def test_params_with_preset() -> None:
    class P(Params):
        width = Float(default=10.0)
        length = 15.0
        presets = (Preset("large", width=50.0, length=40.0),)

    assert len(P.presets) == 1
    assert P.presets[0].name == "large"


def test_params_requires_field_type() -> None:
    with pytest.raises(ParamsError, match="must be a dataclass field"):

        class P(Params):
            width = object()


def test_preset_unknown_field() -> None:
    with pytest.raises(ParamsError, match="references unknown field"):

        class P(Params):
            width = Float(default=10.0)
            presets = (Preset("bogus", width=50.0, height=30.0),)


def test_params_presets_defined() -> None:
    class P(Params):
        width = Float(default=10.0)
        presets = (Preset("large", width=50.0),)

    assert len(P.presets) == 1
    assert P.presets[0].name == "large"


def test_params_preset_invalid_type() -> None:
    with pytest.raises(ParamsError, match="must be a Preset instance"):

        class BadModel(Params):
            width = Float(default=10.0)
            presets = ("not_a_preset",)


def test_params_values_resolved_on_class() -> None:
    class P(Params):
        width = Float(default=10.0)
        count = Int(default=3)
        thing = Str(default="nope")

    assert P.width == 10.0
    assert P.count == 3
    assert P.thing == "nope"


def test_params_default_values() -> None:
    class P(Params):
        width = Float(default=10.0)
        count = Int(default=3)
        thing = Str(default="nope")

    p = P()
    assert p.width == 10.0
    assert p.count == 3
    assert p.thing == "nope"


def test_params_override() -> None:
    class P(Params):
        width: float = Float(default=10.0)
        count: int = Int(default=3)
        thing: str = Str(default="nope")

    p = P(width=20.0, thing="yep")
    assert p.width == 20.0
    assert p.count == 3
    assert p.thing == "yep"


def test_params_override_out_of_range() -> None:
    class P(Params):
        width = Float(default=10.0, min=5.0, max=100.0)

    with pytest.raises(ParamValidationError, match=r"must be <= max"):
        P(width=999.0)  # ty: ignore[unknown-argument]


def test_params_override_invalid() -> None:
    class P(Params):
        width = Float(default=10.0)

    with pytest.raises(TypeError):
        P(nonexistent=42)  # ty: ignore[unknown-argument]


def test_params_preset_selected() -> None:
    class P(Params):
        width = Float(default=10.0)
        count = Int(default=3)
        presets = (Preset("large", width=50.0, count=8),)

    p = P.with_preset("large")
    assert p.width == 50.0
    assert p.count == 8


def test_params_preset_and_override() -> None:
    class P(Params):
        width = Float(default=10.0)
        presets = (Preset("large", width=50.0),)

    p = P.with_preset("large", width=25.0)
    assert p.width == 25.0


def test_params_unknown_preset_raises() -> None:
    class P(Params):
        width = Float(default=10.0)
        presets = (Preset("large", width=50.0),)

    with pytest.raises(ParamsError, match="Unknown preset"):
        P.with_preset("typo")


def test_params_multiple_instances_independent() -> None:
    class P(Params):
        width = Float(default=10.0)

    p1 = P()
    p2 = P(width=99.0)  # ty: ignore[unknown-argument]
    assert p1.width == 10.0
    assert p2.width == 99.0


def test_params_subclass_inherits_fields() -> None:
    class Base(Params):
        width = Float(default=10.0)

    class Child(Base):
        height = Float(default=5.0)

    p = Child()
    assert p.width == 10.0
    assert p.height == 5.0


def test_params_subclass_does_not_mutate_parent_fields() -> None:
    class Base(Params):
        width = Float(default=10.0)

    class Child(Base):
        height = Float(default=5.0)

    assert not hasattr(Base, "height")


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        pytest.param(
            {}, {"x": 1.0, "n": 3, "flag": False, "label": "hello"}, id="empty"
        ),
        pytest.param({"x": 11.5}, {"x": 11.5}, id="float"),
        pytest.param({"x": 5}, {"x": 5.0}, id="float_coercion"),
        pytest.param({"n": 8}, {"n": 8}, id="int"),
        pytest.param({"n": 7.9}, {"n": 7}, id="int_coercion"),
        pytest.param(
            {"n": 7.9, "x": 5}, {"n": 7, "x": 5.0}, id="multi_coercion"
        ),
        pytest.param(
            {"n": 2, "x": 17.5, "flag": 1},
            {"n": 2, "x": 17.5, "flag": True},
            id="multi",
        ),
        pytest.param({"flag": 1}, {"flag": True}, id="bool_true"),
        pytest.param({"flag": 0}, {"flag": False}, id="bool_false"),
        pytest.param({"label": "world"}, {"label": "world"}, id="str"),
        pytest.param(
            {"does_not_exist": "aa23"}, {}, id="ignore_unknown_field"
        ),
    ],
)
def test_apply_overrides(
    model_base: type[Params],
    overrides: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    class Target:
        x: float = 1.0
        n: int = 3
        flag: bool = False
        label: str = "hello"

    class T(Target, model_base):  # ty: ignore[unsupported-base]
        pass

    target = T()
    run_state.param_overrides = overrides
    run_state.apply_overrides(target)
    for name, value in expected.items():
        assert getattr(target, name) == value
    assert isinstance(target.x, float)
    assert isinstance(target.n, int)
    assert isinstance(target.flag, bool)
    assert isinstance(target.label, str)


def test_apply_overrides_enum(model_base: type[Params]) -> None:
    class Color(Enum):
        RED = "red"
        BLUE = "blue"
        PURPLE = "purple"

    class T(model_base):  # ty: ignore[unsupported-base]
        color: Color = Color.RED

    target = T()
    run_state.param_overrides = {"color": "blue"}
    run_state.apply_overrides(target)
    assert target.color == Color.BLUE


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        pytest.param(
            {"label": None},
            {"label": None, "size": "small"},
            id="optional_none",
        ),
        pytest.param(
            {"label": "world"},
            {"label": "world", "size": "small"},
            id="optional_value",
        ),
        pytest.param(
            {"size": "large"},
            {"label": "hello", "size": "large"},
            id="literal",
        ),
    ],
)
def test_apply_overrides_misc(
    model_base: type[Params],
    overrides: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    class T(model_base):  # ty: ignore[unsupported-base]
        label: str | None = "hello"
        size: Literal["small", "medium", "large"] = "small"

    target = T()
    run_state.param_overrides = overrides
    run_state.apply_overrides(target)
    for name, value in expected.items():
        assert getattr(target, name) == value


def test_apply_overrides_nested_dataclass(model_base: type[Params]) -> None:

    @dataclass
    class Point:
        x: float = 0.0
        y: float = 0.0

    @dataclass
    class NestedNestedT:
        point: Point = field(default_factory=Point)

    @dataclass
    class NestedT:
        point: Point = field(default_factory=Point)
        nested: NestedNestedT = field(default_factory=NestedNestedT)
        several: Sequence[NestedNestedT] = field(default_factory=list)

    class T(model_base):  # ty: ignore[unsupported-base]
        count: int = 0
        nested: NestedT = field(
            default_factory=lambda: NestedT(Point(30.0, 40.0))
        )
        point: Point = field(default_factory=lambda: Point(10.0, 20.0))
        top_several: Sequence[NestedNestedT] = field(default_factory=list)

    run_state.param_overrides = {
        "point": {"x": 3.0, "y": 4.0},
        "nested": {
            "point": {"x": 1.5, "y": 2.5},
            "nested": {"point": {"x": 9.9, "y": 8.8}},
            "several": [
                {"point": {"x": 1.1, "y": 1.111}},
                {"point": {"x": 2.2, "y": 2.222}},
            ],
        },
        "top_several": [
            {"point": {"x": 4.4, "y": 4.444}},
            {"point": {"x": 5.5, "y": 5.555}},
        ],
    }
    t = T()
    run_state.apply_overrides(t)
    expected = T(
        count=0,
        point=Point(x=3.0, y=4.0),
        nested=NestedT(
            nested=NestedNestedT(point=Point(x=9.9, y=8.8)),
            point=Point(x=1.5, y=2.5),
            several=(
                NestedNestedT(point=Point(x=1.1, y=1.111)),
                NestedNestedT(point=Point(x=2.2, y=2.222)),
            ),
        ),
        top_several=(
            NestedNestedT(point=Point(x=4.4, y=4.444)),
            NestedNestedT(point=Point(x=5.5, y=5.555)),
        ),
    )
    assert t == expected
