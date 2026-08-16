"""Geometry collection utility tests."""

from __future__ import annotations

import sys
from contextlib import suppress
from dataclasses import dataclass
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
    from collections.abc import Sequence

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


@dataclass
class ShowableObject:
    @classmethod
    def test_cases(cls) -> Sequence[Any]:
        def _case(obj: object, name: str | None = None) -> Any:
            return pytest.param(obj, id=(name or type(obj).__name__))

        return (
            _case(MockBuild123d.Shape()),
            _case(MockBuild123d.Compound()),
            _case(MockBuild123d.Builder(shape=MockBuild123d.Shape())),
            _case(MockBuild123d.Builder(), "empty_builder"),
            _case(MockBuild123d.Location()),
            _case(
                MockBuild123d.LocationList(
                    [MockBuild123d.Location(), MockBuild123d.Location()]
                ),
                "location_list",
            ),
            _case(
                MockBuild123d.LocationList([MockBuild123d.Location()]),
                "single_location_list",
            ),
            _case(MockBuild123d.LocationList(), "empty_location_list"),
            _case(MockBuild123d.Plane()),
            _case(
                MockBuild123d.Joint(
                    parent=MockBuild123d.Compound(
                        bound_box=MockBuild123d.BoundBox(diagonal=24)
                    )
                )
            ),
        )

    @classmethod
    def for_object(
        cls, obj: object, max_diagonal: float = 0
    ) -> MockBuild123d.Shape | None:
        if isinstance(obj, MockBuild123d.Shape):
            return obj
        if isinstance(obj, MockBuild123d.Builder):
            return obj.shape
        if isinstance(obj, MockBuild123d.Location):
            axes_scale = max_diagonal / 12 or 10
            return cls._make_triad(
                label=type(obj).__name__, axes_scale=axes_scale, location=obj
            )
        if isinstance(obj, MockBuild123d.LocationList):
            expected_objects = [
                eo
                for loc in obj.locations
                if (eo := cls.for_object(loc, max_diagonal=max_diagonal))
            ]
            if not expected_objects:
                return None
            if len(expected_objects) == 1:
                return expected_objects[0]
            return MockBuild123d.Compound(
                children=expected_objects, label="LocationList"
            )
        if isinstance(obj, MockBuild123d.Plane):
            axes_scale = max_diagonal / 12 or 10
            return cls._make_triad(
                label=type(obj).__name__,
                axes_scale=axes_scale,
                location=obj.location,
            )
        if isinstance(obj, MockBuild123d.Joint):
            symbol = obj.symbol
            symbol.label = f"{obj.label} {type(obj).__name__}"
            return symbol
        return None

    @classmethod
    def for_objects(
        cls, obj: Sequence[object], max_diagonal: float = 0
    ) -> tuple[MockBuild123d.Shape, ...]:
        expected_objects = []
        for o in obj:
            if bb := getattr(o, "bound_box", None):
                max_diagonal = max(max_diagonal, bb.diagonal)
            if expected := cls.for_object(o, max_diagonal=max_diagonal):
                expected_objects.append(expected)
        return tuple(expected_objects)

    @classmethod
    def max_diagonal(
        cls, obj: Sequence[object], max_diagonal: float = 0
    ) -> float:
        for o in obj:
            if bb := getattr(o, "bound_box", None):
                max_diagonal = max(max_diagonal, bb.diagonal)
        return max_diagonal

    @classmethod
    def compound_for_objects(
        cls, objects: Sequence[object], label: str = ""
    ) -> MockBuild123d.Compound:
        return MockBuild123d.Compound(
            children=cls.for_objects(objects), label=label
        )

    @classmethod
    def _make_triad(
        cls, label: str, axes_scale: float, location: MockBuild123d.Location
    ) -> MockBuild123d.Compound:
        symbol = MockBuild123d.Compound.make_triad(axes_scale=axes_scale).move(
            location
        )
        symbol.label = label
        return symbol


@pytest.fixture(params=ShowableObject.test_cases())
def showable_object(
    request: pytest.FixtureRequest, mock_b123d: MockBuild123d
) -> object:
    return request.param


@pytest.fixture
def preshown_geometry(
    mock_b123d: MockBuild123d, show_callable: ShowCallable
) -> tuple[object, ...]:
    preshown_geometry = (
        object(),
        mock_b123d.Shape(bound_box=mock_b123d.BoundBox(diagonal=12)),
        mock_b123d.Builder(),
        mock_b123d.Builder(shape=mock_b123d.Shape()),
    )
    for preshown_obj in preshown_geometry:
        show_callable(preshown_obj)  # ty: ignore [invalid-argument-type]
    assert run_state.geometry.resolve() == ShowableObject.compound_for_objects(
        preshown_geometry, label="bdbox collected geometry"
    )
    return preshown_geometry


def test_show_multiple_args(
    mock_b123d: MockBuild123d,
    show_callable: ShowCallable,
    showable_object: object,
) -> None:
    shown_geometry = (
        object(),
        mock_b123d.Shape(),
        showable_object,
        mock_b123d.Builder(shape=mock_b123d.Shape()),
        object(),
        mock_b123d.Shape(),
    )
    show_callable(*shown_geometry)  # ty: ignore [invalid-argument-type]
    assert run_state.geometry.resolve() == ShowableObject.compound_for_objects(
        shown_geometry, label="bdbox collected geometry"
    )


def test_geometry_resolve_returns_show_multiple(
    mock_b123d: MockBuild123d,
    show_callable: ShowCallable,
    showable_object: object,
) -> None:
    shown_geometry = (
        mock_b123d.Shape(),
        object(),
        mock_b123d.Shape(),
        showable_object,
        object(),
        mock_b123d.Builder(shape=mock_b123d.Shape()),
        mock_b123d.Builder(),
    )
    for obj in shown_geometry:
        show_callable(obj)  # ty: ignore [invalid-argument-type]
    assert run_state.geometry.resolve() == ShowableObject.compound_for_objects(
        shown_geometry, label="bdbox collected geometry"
    )


def test_geometry_resolve_returns_show_single(showable_object: object) -> None:
    show(showable_object)  # ty: ignore [invalid-argument-type]
    expected_object = ShowableObject.for_object(showable_object)
    assert run_state.geometry.resolve() == expected_object


@pytest.mark.usefixtures("preshown_geometry")
def test_geometry_resolve_returns_shown_with_floordiv_operator(
    show_callable: ShowCallable, showable_object: object
) -> None:
    with suppress(ModelExit):
        show_callable // showable_object  # ty: ignore [unsupported-operator]
    if expected_object := ShowableObject.for_object(showable_object):
        expected_object.label = "bdbox selection"
    resolved = run_state.geometry.resolve()
    assert resolved == expected_object


def test_geometry_resolve_returns_shown_with_truediv_operator(
    mock_b123d: MockBuild123d,
    show_callable: ShowCallable,
    preshown_geometry: tuple[object, ...],
    showable_object: object,
) -> None:
    with suppress(ModelExit):
        show_callable / showable_object  # ty: ignore [unsupported-operator]
    expected = ShowableObject.for_objects(preshown_geometry)
    if expected_object := ShowableObject.for_object(
        showable_object, max_diagonal=ShowableObject.max_diagonal(expected)
    ):
        expected_object.label = "bdbox selection"
        expected = (*expected, expected_object)
    resolved = run_state.geometry.resolve()
    assert resolved == mock_b123d.Compound(
        children=expected, label="bdbox collected geometry"
    )


def test_geometry_resolve_returns_shown_with_add_operator(
    mock_b123d: MockBuild123d,
    show_callable: ShowCallable,
    preshown_geometry: tuple[object, ...],
    showable_object: object,
) -> None:
    with suppress(ModelExit):
        show_callable + showable_object  # ty: ignore [unsupported-operator]
    expected = ShowableObject.for_objects(preshown_geometry)
    if expected_object := ShowableObject.for_object(
        showable_object, max_diagonal=ShowableObject.max_diagonal(expected)
    ):
        expected_object.label = "bdbox highlight"
        expected = (*expected, expected_object)
    resolved = run_state.geometry.resolve()
    assert resolved == mock_b123d.Compound(
        children=expected, label="bdbox collected geometry"
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
    monkeypatch: pytest.MonkeyPatch,
    mock_b123d: MockBuild123d,
    showable_object: object,
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
        custom_showable_object: object

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
    mock_main.custom_showable_object = showable_object
    expected_showable_objects = []
    if expected_showable_object := ShowableObject.for_object(showable_object):
        expected_showable_object.label = "custom_showable_object"
        expected_showable_objects.append(expected_showable_object)
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
            *expected_showable_objects,
        ],
        label="bdbox collected geometry",
    )
