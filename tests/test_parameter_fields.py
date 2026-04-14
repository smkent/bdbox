"""Parameter system fields tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from bdbox.errors import ParamsError, ParamValidationError
from bdbox.model import Model
from bdbox.parameters.field_factories import Bool, Choice, Float, Int, Str
from bdbox.parameters.fields import (
    BoolField,
    ChoiceField,
    Field,
    FloatField,
    IntField,
    StrField,
)
from bdbox.parameters.preset import Preset

if TYPE_CHECKING:
    from collections.abc import Callable
    from dataclasses import Field as DCField


@pytest.mark.parametrize(
    ("factory", "field", "default"),
    [
        pytest.param(Float, FloatField, 10.0, id="FloatField"),
        pytest.param(Int, IntField, 3, id="IntField"),
        pytest.param(Bool, BoolField, True, id="BoolField[True]"),
        pytest.param(Bool, BoolField, False, id="BoolField[False]"),
        pytest.param(Str, StrField, "hyperspace", id="StrField"),
    ],
)
@pytest.mark.parametrize(
    "description",
    [
        pytest.param("helpful hint for this field", id="description"),
        pytest.param(None, id="no_description"),
    ],
)
def test_field_basics(
    factory: Callable[..., DCField],
    field: type[Field],
    default: Any,
    description: str,
) -> None:
    kwargs = {"default": default}
    if description:
        kwargs["description"] = description
    f = Field.from_dataclass_field(factory(**kwargs))
    assert isinstance(f, field)
    assert f.default == default
    assert f.description == description


def test_float_all_attrs() -> None:
    f = Field.from_dataclass_field(
        Float(default=10.0, min=5.0, max=100.0, step=0.5, description="Width")
    )
    assert isinstance(f, FloatField)
    assert f.min == 5.0
    assert f.max == 100.0
    assert f.step == 0.5
    assert f.description == "Width"


@pytest.mark.parametrize(
    ("func", "expected_match"),
    [
        pytest.param(
            lambda: Float(default=10.0, min=50.0, max=5.0),
            r"min.*must be <= max",
            id="min_gt_max",
        ),
        pytest.param(
            lambda: Float(default=1.0, min=5.0),
            r"default.*must be >= min",
            id="below_min",
        ),
        pytest.param(
            lambda: Float(default=200.0, max=100.0),
            r"default.*must be <= max",
            id="above_max",
        ),
        pytest.param(
            lambda: Float(default=10.0, step=0.0),
            r"step.*must be > 0",
            id="zero_step",
        ),
        pytest.param(
            lambda: Float(default=10.0, step=-1.0),
            r"step.*must be > 0",
            id="negative_step",
        ),
    ],
)
def test_float_raises(func: Callable[[], None], expected_match: str) -> None:
    with pytest.raises(ParamsError, match=expected_match):
        func()


def test_int_all_attrs() -> None:
    i = Field.from_dataclass_field(
        Int(default=3, min=1, max=10, step=1, description="Count")
    )
    assert isinstance(i, IntField)
    assert i.min == 1
    assert i.max == 10
    assert i.step == 1
    assert i.description == "Count"


@pytest.mark.parametrize(
    ("func", "expected_match"),
    [
        pytest.param(
            lambda: Int(default=5, min=10, max=1),
            r"min.*must be <= max",
            id="min_gt_max",
        ),
        pytest.param(
            lambda: Int(default=0, min=1),
            r"default.*must be >= min",
            id="below_min",
        ),
        pytest.param(
            lambda: Int(default=11, max=10),
            r"default.*must be <= max",
            id="above_max",
        ),
        pytest.param(
            lambda: Int(default=5, step=0),
            r"step.*must be > 0",
            id="zero_step",
        ),
        pytest.param(
            lambda: Int(default=5, step=-2),
            r"step.*must be > 0",
            id="negative_step",
        ),
    ],
)
def test_int_raises(func: Callable[[], None], expected_match: str) -> None:
    with pytest.raises(ParamsError, match=expected_match):
        func()


def test_str_all_attrs() -> None:
    s = Field.from_dataclass_field(
        Str(default="hello", min_length=3, max_length=10, description="Label")
    )
    assert isinstance(s, StrField)
    assert s.min_length == 3
    assert s.max_length == 10
    assert s.description == "Label"


@pytest.mark.parametrize(
    ("func", "expected_match"),
    [
        pytest.param(
            lambda: Str(default="hello", min_length=10, max_length=3),
            r"min.*must be <= max",
            id="min_gt_max",
        ),
        pytest.param(
            lambda: Str(default="hi", min_length=5),
            r"default.*must be >= min",
            id="below_min",
        ),
        pytest.param(
            lambda: Str(default="hello world", max_length=5),
            r"default.*must be <= max",
            id="above_max",
        ),
    ],
)
def test_str_raises(func: Callable[[], None], expected_match: str) -> None:
    with pytest.raises(ParamsError, match=expected_match):
        func()


def test_choice_valid() -> None:
    c = Field.from_dataclass_field(
        Choice(default="solid", choices=["solid", "hollow"])
    )
    assert isinstance(c, ChoiceField)
    assert c.default == "solid"
    assert c.choices == ["solid", "hollow"]
    assert c.description is None


def test_choice_invalid() -> None:
    with pytest.raises(ParamsError, match=r"Choice default .* is not in"):
        Choice(default="invalid", choices=["solid", "hollow"])


def test_choice_with_description() -> None:
    c: ChoiceField = Field.from_dataclass_field(
        Choice(default="a", choices=["a", "b"], description="Style")
    )  # ty: ignore[invalid-assignment]
    assert c.description == "Style"


def test_choice_int_values() -> None:
    c = Field.from_dataclass_field(Choice(default=4, choices=[2, 4, 8, 16]))
    assert isinstance(c, ChoiceField)
    assert c.default == 4
    assert c.choices == [2, 4, 8, 16]


def test_choice_float_values() -> None:
    c = Field.from_dataclass_field(
        Choice(default=0.5, choices=[0.5, 1.0, 2.0])
    )
    assert isinstance(c, ChoiceField)
    assert c.default == 0.5
    assert c.choices == [0.5, 1.0, 2.0]


def test_choice_int_invalid_default() -> None:
    with pytest.raises(ParamsError, match="not in choices"):
        Choice(default=3, choices=[2, 4, 8])


def test_choice_mixed_types_rejected() -> None:
    with pytest.raises(ParamsError, match="same type"):
        Choice(default="wood", choices=["wood", 1, "metal"])


def test_choice_int_float_mixed_rejected() -> None:
    with pytest.raises(ParamsError, match="same type"):
        Choice(default=1, choices=[1, 2.0, 3])


def test_choice_bool_int_mixed_rejected() -> None:
    with pytest.raises(ParamsError, match="same type"):
        Choice(default=True, choices=[True, 1, False])


def test_choice_bool_values() -> None:
    c = Field.from_dataclass_field(Choice(default=True, choices=[True, False]))
    assert isinstance(c, ChoiceField)
    assert c.default is True
    assert list(c.choices) == [True, False]


def test_choice_field_validate_invalid() -> None:
    cf = ChoiceField("wood", ["wood", "metal", "plastic"])
    with pytest.raises(ParamValidationError, match="not in choices"):
        cf.validate("aluminum")


def test_choice_field_annotation_with_description() -> None:
    class M(Model):
        material = Choice("wood", ["wood", "metal"], description="Material")

    assert M().material == "wood"


def test_choice_field_annotation_without_description() -> None:
    class M(Model):
        side_count = Choice(6, [3, 4, 6, 8, 12])

    assert M().side_count == 6


def test_preset_basic() -> None:
    p = Preset("large", width=50.0, count=5)
    assert p.name == "large"
    assert p.description is None
    assert p.values == {"width": 50.0, "count": 5}


def test_preset_with_description() -> None:
    p = Preset("large", description="Full size", width=50.0)
    assert p.description == "Full size"
    assert p.values == {"width": 50.0}


def test_preset_no_values() -> None:
    p = Preset("empty")
    assert p.values == {}
