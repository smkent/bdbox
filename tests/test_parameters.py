"""Params base class tests."""

from __future__ import annotations

from dataclasses import fields

import pytest

from bdbox.errors import ParamsError, ParamValidationError
from bdbox.parameters.field_factories import Float, Int, Str
from bdbox.parameters.parameters import Params
from bdbox.parameters.preset import Preset


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
