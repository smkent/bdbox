"""Geometry collection utility tests."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import TYPE_CHECKING, Any

from bdbox.geometry import resolve_geometry, show

if TYPE_CHECKING:
    import pytest

    from tests.utils import MockBuild123d


class MockMainBase(ModuleType):
    count: int

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("__main__", *args, **kwargs)


def test_show_multiple_args(mock_b123d: MockBuild123d) -> None:
    obj0, obj1, obj2, obj3, obj4 = (
        object(),
        mock_b123d.Shape(),
        mock_b123d.Shape(),
        mock_b123d.Shape(),
        object(),
    )
    show(obj0, obj1, obj2, obj3, obj4)
    assert resolve_geometry() == [obj1, obj2, obj3]


def test_resolve_geometry_returns_shown(mock_b123d: MockBuild123d) -> None:
    obj1, obj2, obj3, obj4 = (
        mock_b123d.Shape(),
        object(),
        mock_b123d.Shape(),
        object(),
    )
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
    monkeypatch: pytest.MonkeyPatch, mock_b123d: MockBuild123d
) -> None:
    class MockMain(MockMainBase):
        count: int

    mock_main = MockMain()
    monkeypatch.setitem(sys.modules, "__main__", mock_main)

    mock_main.count = 42
    assert resolve_geometry() == []


def test_scan_main_globals_returns_shapes(
    monkeypatch: pytest.MonkeyPatch, mock_b123d: MockBuild123d
) -> None:
    shape1, shape2 = mock_b123d.Shape(), mock_b123d.Shape()

    class MockMain(MockMainBase):
        count: int
        box: mock_b123d.Shape
        sphere: mock_b123d.Shape
        _private: mock_b123d.Shape

    mock_main = MockMain()
    mock_main.box = shape1
    mock_main.sphere = shape2
    mock_main._private = mock_b123d.Shape()  # noqa: SLF001
    mock_main.count = 42
    monkeypatch.setitem(sys.modules, "__main__", mock_main)

    assert set(resolve_geometry()) == {shape1, shape2}
