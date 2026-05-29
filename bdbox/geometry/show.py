from __future__ import annotations

from typing import TYPE_CHECKING

from bdbox.runner.state import run_state

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from build123d import Compound, Shape


def show(
    *geometry: Compound
    | Shape
    | Sequence[Compound | Shape]
    | Mapping[str, Compound | Shape],
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
