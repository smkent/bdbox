"""Geometry collection utility tests."""

from __future__ import annotations

import sys
from contextlib import suppress
from types import ModuleType
from typing import TYPE_CHECKING, Any

import pytest

from bdbox.errors import ModelExit
from bdbox.geometry.show import show
from bdbox.model.model import Model
from bdbox.model.parameters import Params
from bdbox.runner.state import run_state
from tests.utils import MockBuild123d

if TYPE_CHECKING:
    from bdbox.geometry.show import ShowCallable


class MockMainBase(ModuleType):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("__main__", *args, **kwargs)


@pytest.fixture(
    params=[
        pytest.param(show, id="show"),
        pytest.param(Params.show, id="Params.show"),
        pytest.param(Model.show, id="Model.show"),
    ]
)
def show_callable(request: pytest.FixtureRequest) -> ShowCallable:
    assert request.param is show
    return request.param


def test_show_multiple_args(
    mock_b123d: MockBuild123d, show_callable: ShowCallable
) -> None:
    obj0, obj1, obj2, obj3, obj4 = (
        object(),
        mock_b123d.Shape(),
        mock_b123d.Builder(shape=mock_b123d.Shape()),
        mock_b123d.Shape(),
        object(),
    )
    show_callable(obj0, obj1, obj2, obj3, obj4)  # ty: ignore [invalid-argument-type]
    assert obj2.shape
    assert run_state.geometry.resolve() == mock_b123d.Compound(
        children=[obj1, obj2.shape, obj3], label="bdbox collected geometry"
    )


def test_geometry_resolve_returns_show_multiple(
    mock_b123d: MockBuild123d, show_callable: ShowCallable
) -> None:
    expected: list[mock_b123d.Shape] = []
    for obj in (
        mock_b123d.Shape(),
        object(),
        mock_b123d.Shape(),
        object(),
        mock_b123d.Builder(shape=mock_b123d.Shape()),
        mock_b123d.Builder(),
    ):
        show_callable(obj)  # ty: ignore [invalid-argument-type]
        if isinstance(obj, mock_b123d.Builder) and obj.shape:
            expected.append(obj.shape)
        elif isinstance(obj, mock_b123d.Shape):
            expected.append(obj)
    assert run_state.geometry.resolve() == mock_b123d.Compound(
        children=expected, label="bdbox collected geometry"
    )


@pytest.mark.parametrize(
    "obj",
    [
        pytest.param(object(), id="object"),
        pytest.param(MockBuild123d.Shape(), id="shape"),
        pytest.param(MockBuild123d.Builder(), id="empty_builder"),
        pytest.param(
            MockBuild123d.Builder(shape=MockBuild123d.Shape()), id="builder"
        ),
    ],
)
def test_geometry_resolve_returns_show_single(
    mock_b123d: MockBuild123d, obj: object
) -> None:
    show(obj)  # ty: ignore [invalid-argument-type]
    expected = None
    if isinstance(obj, mock_b123d.Builder) and obj.shape:
        expected = obj.shape
    elif isinstance(obj, mock_b123d.Shape):
        expected = obj
    assert run_state.geometry.resolve() == expected


@pytest.mark.parametrize(
    "obj",
    [
        pytest.param(object(), id="object"),
        pytest.param(MockBuild123d.Shape(), id="shape"),
        pytest.param(MockBuild123d.Builder(), id="empty_builder"),
        pytest.param(
            MockBuild123d.Builder(shape=MockBuild123d.Shape()), id="builder"
        ),
    ],
)
def test_geometry_resolve_returns_shown_with_truediv_operator(
    mock_b123d: MockBuild123d, show_callable: ShowCallable, obj: object
) -> None:
    preloaded_shapes = [mock_b123d.Shape(), mock_b123d.Shape()]
    for preload_obj in (
        object(),
        preloaded_shapes[0],
        mock_b123d.Builder(),
        mock_b123d.Builder(shape=preloaded_shapes[1]),
    ):
        show_callable(preload_obj)  # ty: ignore [invalid-argument-type]
    assert run_state.geometry.resolve() == mock_b123d.Compound(
        children=preloaded_shapes, label="bdbox collected geometry"
    )
    with suppress(ModelExit):
        show_callable / obj  # ty: ignore [unsupported-operator]
    expected = None
    if isinstance(obj, mock_b123d.Builder) and obj.shape:
        expected = obj.shape
    elif isinstance(obj, mock_b123d.Shape):
        expected = obj
    resolved = run_state.geometry.resolve()
    assert resolved == expected
    if resolved:
        assert resolved.label == "bdbox selection"


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
