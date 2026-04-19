"""Geometry collection utility tests."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest

from bdbox.geometry import reset_geometry, resolve_geometry, show


@pytest.fixture(autouse=True)
def _reset_geometry() -> None:
    """Reset collected geometry before and after each test."""
    reset_geometry()


class MockBuild123d(ModuleType):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("build123d", *args, **kwargs)

    class Shape:
        pass


class MockMainBase(ModuleType):
    count: int

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("__main__", *args, **kwargs)


@pytest.fixture(autouse=True)
def b123d(monkeypatch: pytest.MonkeyPatch) -> MockBuild123d:
    module = MockBuild123d()
    monkeypatch.setitem(sys.modules, "build123d", module)
    return module


def test_show_multiple_args(b123d: MockBuild123d) -> None:
    obj0, obj1, obj2, obj3, obj4 = (
        object(),
        b123d.Shape(),
        b123d.Shape(),
        b123d.Shape(),
        object(),
    )
    show(obj0, obj1, obj2, obj3, obj4)
    assert resolve_geometry() == [obj1, obj2, obj3]


def test_resolve_geometry_returns_shown(b123d: MockBuild123d) -> None:
    obj1, obj2, obj3, obj4 = b123d.Shape(), object(), b123d.Shape(), object()
    show(obj1)
    show(obj2)
    show(obj3)
    show(obj4)
    assert resolve_geometry() == [obj1, obj3]


def test_resolve_geometry_empty_no_build123d(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "build123d", raising=False)
    assert resolve_geometry() == []


def test_scan_main_globals_no_shapes(
    monkeypatch: pytest.MonkeyPatch, b123d: MockBuild123d
) -> None:
    class MockMain(MockMainBase):
        count: int

    mock_main = MockMain()
    monkeypatch.setitem(sys.modules, "__main__", mock_main)

    mock_main.count = 42
    assert resolve_geometry() == []


def test_scan_main_globals_returns_shapes(
    monkeypatch: pytest.MonkeyPatch, b123d: MockBuild123d
) -> None:
    shape1, shape2 = b123d.Shape(), b123d.Shape()

    class MockMain(MockMainBase):
        count: int
        box: b123d.Shape
        sphere: b123d.Shape
        _private: b123d.Shape

    mock_main = MockMain()
    mock_main.box = shape1
    mock_main.sphere = shape2
    mock_main._private = b123d.Shape()  # noqa: SLF001
    mock_main.count = 42
    monkeypatch.setitem(sys.modules, "__main__", mock_main)

    assert set(resolve_geometry()) == {shape1, shape2}
