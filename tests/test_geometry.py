"""Geometry collection utility tests."""

from __future__ import annotations

import sys
import types
from typing import Protocol, cast

import pytest

import bdbox.geometry as geom
from bdbox.geometry import resolve_geometry, show


@pytest.fixture(autouse=True)
def _clear_geometry() -> None:
    """Reset collected geometry before and after each test."""
    geom._geometry.clear()  # noqa: SLF001


def test_show_multiple_args() -> None:
    obj1, obj2, obj3 = object(), object(), object()
    show(obj1, obj2, obj3)
    assert resolve_geometry() == [obj1, obj2, obj3]


def test_resolve_geometry_returns_shown() -> None:
    obj1, obj2 = object(), object()
    show(obj1)
    show(obj2)
    assert resolve_geometry() == [obj1, obj2]


def test_resolve_geometry_empty_no_build123d(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "build123d", raising=False)
    assert resolve_geometry() == []


def test_scan_main_globals_no_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockBuild123d(Protocol):
        Shape: type

    fake_shape_cls = type("Shape", (), {})
    fake_b123d = cast("MockBuild123d", types.ModuleType("build123d"))
    fake_b123d.Shape = fake_shape_cls
    monkeypatch.setitem(sys.modules, "build123d", fake_b123d)

    class MockMain(Protocol):
        count: int

    fake_main = cast("MockMain", types.ModuleType("__main__"))
    fake_main.count = 42
    monkeypatch.setitem(sys.modules, "__main__", fake_main)

    assert resolve_geometry() == []


def test_scan_main_globals_returns_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockBuild123d(Protocol):
        Shape: type

    fake_shape_cls = type("Shape", (), {})
    fake_b123d = cast("MockBuild123d", types.ModuleType("build123d"))
    fake_b123d.Shape = fake_shape_cls
    monkeypatch.setitem(sys.modules, "build123d", fake_b123d)

    class MockMain(Protocol):
        count: int
        box: fake_b123d.Shape
        sphere: fake_b123d.Shape
        _private: fake_b123d.Shape

    shape1, shape2 = fake_shape_cls(), fake_shape_cls()
    fake_main = cast("MockMain", types.ModuleType("__main__"))
    fake_main.box = shape1
    fake_main.sphere = shape2
    fake_main._private = fake_shape_cls()  # noqa: SLF001
    fake_main.count = 42
    monkeypatch.setitem(sys.modules, "__main__", fake_main)

    result = resolve_geometry()
    assert set(result) == {shape1, shape2}
