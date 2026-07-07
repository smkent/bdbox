"""Geometry collection utility tests."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import TYPE_CHECKING, Any

import pytest

from bdbox.geometry.show import show
from bdbox.runner.state import run_state

if TYPE_CHECKING:
    from tests.utils import MockBuild123d


class MockMainBase(ModuleType):
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
    show(obj0, obj1, obj2, obj3, obj4)  # ty: ignore [invalid-argument-type]
    assert run_state.geometry.resolve() == mock_b123d.Compound(
        children=[obj1, obj2, obj3], label="bdbox collected geometry"
    )


def test_geometry_resolve_returns_shown(mock_b123d: MockBuild123d) -> None:
    obj1, obj2, obj3, obj4, obj5, obj6 = (
        mock_b123d.Shape(),
        object(),
        mock_b123d.Shape(),
        object(),
        mock_b123d.Builder(shape=mock_b123d.Shape()),
        mock_b123d.Builder(),
    )
    show(obj1)  # ty: ignore [invalid-argument-type]
    show(obj2)  # ty: ignore [invalid-argument-type]
    show(obj3)  # ty: ignore [invalid-argument-type]
    show(obj4)  # ty: ignore [invalid-argument-type]
    show(obj5)  # ty: ignore [invalid-argument-type]
    show(obj6)  # ty: ignore [invalid-argument-type]
    assert obj5.shape
    assert run_state.geometry.resolve() == mock_b123d.Compound(
        children=[obj1, obj3, obj5.shape], label="bdbox collected geometry"
    )


def test_geometry_resolve_empty_no_build123d(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "build123d", raising=False)
    assert run_state.geometry.resolve() is None


@pytest.mark.usefixtures("mock_b123d")
def test_scan_main_globals_no_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockMain(MockMainBase):
        count: int

    mock_main = MockMain()
    monkeypatch.setitem(sys.modules, "__main__", mock_main)

    mock_main.count = 42
    assert run_state.geometry.resolve() is None


def test_scan_main_globals_returns_shapes(
    monkeypatch: pytest.MonkeyPatch, mock_b123d: MockBuild123d
) -> None:
    shape1, shape2, shape3, shape4, shape5, shape6 = (
        mock_b123d.Shape(),
        mock_b123d.Shape(),
        mock_b123d.Shape(),
        mock_b123d.Shape(),
        mock_b123d.Shape(),
        mock_b123d.Shape(),
    )

    class MockMain(MockMainBase):
        count: int
        box: mock_b123d.Shape
        sphere: mock_b123d.Shape
        _private: mock_b123d.Shape
        things: tuple[Any, ...]
        mapping: dict[Any, Any]

    mock_main = MockMain()
    mock_main.box = shape1
    mock_main.sphere = shape2
    mock_main._private = mock_b123d.Shape()  # noqa: SLF001
    mock_main.things = (shape3, [shape4], [shape5, shape6])
    mock_main.mapping = {
        1138: shape1,
        2187: [shape2, {"three_four": [shape3, shape4], 5: shape5}],
        9000: {6.0: shape6},
    }
    mock_main.count = 42
    monkeypatch.setitem(sys.modules, "__main__", mock_main)

    assert run_state.geometry.resolve() == mock_b123d.Compound(
        children=[
            shape1,
            shape2,
            mock_b123d.Compound(
                label="things",
                children=[
                    shape3,
                    shape4,
                    mock_b123d.Compound(children=[shape5, shape6]),
                ],
            ),
            mock_b123d.Compound(
                label="mapping",
                children=[
                    shape1,
                    mock_b123d.Compound(
                        label="2187",
                        children=[
                            shape2,
                            mock_b123d.Compound(
                                children=[
                                    mock_b123d.Compound(
                                        label="three_four",
                                        children=[shape3, shape4],
                                    ),
                                    shape5,
                                ]
                            ),
                        ],
                    ),
                    shape6,
                ],
            ),
        ],
        label="bdbox collected geometry",
    )
