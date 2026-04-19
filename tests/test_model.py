"""Model scaffolding tests."""

from __future__ import annotations

from dataclasses import fields
from typing import Any

import pytest

from bdbox.model import Model
from bdbox.parameters.field_factories import Float, Int, Str
from bdbox.parameters.preset import Preset


def test_model_presets_defined() -> None:
    class MyModel(Model):
        width = Float(default=10.0)
        length = 15.0
        presets = (Preset("large", width=50.0, length=40.0),)

    assert len(MyModel.presets) == 1
    assert MyModel.presets[0].name == "large"


def test_model_no_fields_or_presets() -> None:
    class EmptyModel(Model):
        pass

    assert tuple(f for f in fields(EmptyModel) if f.name != "preset") == ()
    assert EmptyModel.presets == ()


def test_model_default_values() -> None:
    class MyModel(Model):
        width = Float(default=10.0)
        count = Int(default=3)
        thing = Str(default="nope")

    m = MyModel()
    assert m.width == 10.0
    assert m.count == 3
    assert m.thing == "nope"


def test_model_params_override() -> None:
    class MyModel(Model):
        width: float = Float(default=10.0)
        count: int = Int(default=3)
        thing: str = Str(default="nope")

    m = MyModel(width=20.0, thing="yep")
    assert m.width == 20.0
    assert m.count == 3
    assert m.thing == "yep"


def test_model_preset_selected() -> None:
    class MyModel(Model):
        width = Float(default=10.0)
        count = Int(default=3)
        presets = (Preset("large", width=50.0, count=8),)

    m = MyModel.with_preset("large")
    assert m.width == 50.0
    assert m.count == 8


def test_model_preset_and_override() -> None:
    class MyModel(Model):
        width = Float(default=10.0)
        presets = (Preset("large", width=50.0),)

    m = MyModel.with_preset("large", width=25.0)
    assert m.width == 25.0


def test_model_build_raises_not_implemented() -> None:
    class AbstractModel(Model):
        pass

    m = AbstractModel()
    with pytest.raises(NotImplementedError):
        m.build()


def test_model_build_returns_value() -> None:
    class MyModel(Model):
        width = Float(default=10.0)

        def build(self) -> Any:
            return self.width

    m = MyModel()
    assert m.build() == 10.0
