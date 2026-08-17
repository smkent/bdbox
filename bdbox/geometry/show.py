from __future__ import annotations

from dataclasses import dataclass, field
from functools import update_wrapper
from typing import TYPE_CHECKING, Any, ClassVar

from bdbox.errors import ModelExit
from bdbox.runner.state import run_state

if TYPE_CHECKING:
    from typing import Protocol, TypeVar

    from bdbox.geometry.geometry import Geometry

    GeometryT = TypeVar("GeometryT", bound=Geometry | None)

    class ShowCallable(Protocol):
        def __call__(self, *geometry: Geometry | None) -> None: ...


@dataclass
class Show:
    """Extensions for [``show``][bdbox.geometry.show.show]."""

    func: ShowCallable = field(repr=False)

    highlight_mode_colors: ClassVar[dict[str, int]] = {
        "ADD": 0x22FF88,  # green
        "SUBTRACT": 0xFF2351,  # red
        "INTERSECT": 0x22CCFF,  # light blue
        "REPLACE": 0xFF6622,  # orange
        "PRIVATE": 0xBB99FF,  # purple
    }

    def __post_init__(self) -> None:
        update_wrapper(self, self.func)

    def __call__(self, *geometry: Geometry | None) -> Any:
        return self.func(*geometry)

    def __repr__(self) -> str:
        return repr(self.func)

    # Operators

    def __truediv__(self, geometry: GeometryT) -> GeometryT:
        """Show the specified geometry, and stop model execution."""
        if geo := run_state.geometry.filter_geometry(geometry):
            geo.label = "bdbox selection"
            self.func(geo)
        raise ModelExit

    def __floordiv__(self, geometry: GeometryT) -> GeometryT:
        """Show only the specified geometry, and stop model execution."""
        run_state.geometry.__init__()
        return self.__truediv__(geometry)

    def __add__(self, geometry: GeometryT) -> GeometryT:
        """Highlight the specified geometry."""
        if geo := run_state.geometry.filter_geometry(geometry):
            from build123d import Color  # noqa: PLC0415

            geo.label = "bdbox highlight"
            alpha = 0x66
            if (mode := getattr(geo, "mode", None)) and (
                color_name := self.highlight_mode_colors.get(mode.name)
            ) is not None:
                geo.color = Color(color_name, alpha)
            else:
                geo.color = Color(0xFF2351, alpha)
            self.func(geo)
        return geometry


@Show
def show(*geometry: Geometry | None) -> None:
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
