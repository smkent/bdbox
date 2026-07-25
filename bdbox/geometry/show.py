from __future__ import annotations

from dataclasses import dataclass, field
from functools import update_wrapper
from typing import TYPE_CHECKING, Any

from bdbox.errors import ModelExit
from bdbox.runner.state import run_state

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from typing import Protocol, TypeVar

    from build123d import Builder, Compound, Shape

    Geometry = (
        Compound
        | Shape
        | Builder
        | Sequence[Compound | Shape | Builder | None]
        | Mapping[str, Compound | Shape | Builder | None]
        | None
    )

    GeometryT = TypeVar("GeometryT", bound=Geometry)

    class ShowCallable(Protocol):
        def __call__(self, *geometry: Geometry) -> None: ...


@dataclass
class Show:
    """Extensions for [``show``][bdbox.geometry.show.show]."""

    func: ShowCallable = field(repr=False)

    def __post_init__(self) -> None:
        update_wrapper(self, self.func)

    def __call__(self, *geometry: Geometry) -> Any:
        return self.func(*geometry)

    def __repr__(self) -> str:
        return repr(self.func)

    # Operators

    def __truediv__(self, geometry: GeometryT) -> GeometryT:
        """Show only the specified geometry, and stop model execution."""
        run_state.geometry.__init__()
        if geo := run_state.geometry.filter_geometry(geometry):
            geo.label = "bdbox selection"
            self.func(geo)
        raise ModelExit


@Show
def show(
    *geometry: Compound
    | Shape
    | Builder
    | Sequence[Compound | Shape | Builder | None]
    | Mapping[str, Compound | Shape | Builder | None]
    | None,
) -> None:
    """Provide built model geometry for display or use.

    Info:
        With a [``Params``][bdbox.model.parameters.Params] subclass,
        call `show` with your built model geometry. Multiple `show` calls
        accumulate geometry in order.

        With a [``Model``][bdbox.model.model.Model] subclass, return geometry
        from the [``build``][bdbox.model.model.Model.build] method instead of
        calling `show`.

    Note:
        If ``show()`` is never called, bdbox falls back to scanning the
        script's globals for [``build123d.Shape``][topology.Shape] instances,
        but calling ``show()`` manually is recommended.
    """
    return run_state.geometry.accumulate_geometry(*geometry)
