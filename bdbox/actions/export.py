"""STEP file export action."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated

import tyro

from bdbox.errors import Error
from bdbox.geometry import resolve_geometry

from .action import Action

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class ExportAction(Action):
    """Export collected geometry to a STEP or STL file."""

    output: Annotated[
        Path,
        tyro.conf.Positional,
        tyro.conf.arg(
            metavar="output-path", help="Output STEP or STL file path."
        ),
    ]

    @property
    def _exporter(self) -> Callable[..., bool]:
        match self.output.suffix.lower():
            case ".step":
                from build123d import export_step  # noqa: PLC0415

                return export_step
            case ".stl":
                from build123d import export_stl  # noqa: PLC0415

                return export_stl
        raise Error(f"Unknown file type {self.output.suffix}")

    def __call__(self) -> None:
        """Export geometry to a STEP or STL file."""
        geometry = resolve_geometry()
        if not geometry:
            raise Error("No geometry to export")

        from build123d import Compound  # noqa: PLC0415

        shape = Compound(geometry) if len(geometry) > 1 else geometry[0]
        self._exporter(shape, str(self.output))
