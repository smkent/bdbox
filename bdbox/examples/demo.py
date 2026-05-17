from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from build123d import (
    Axis,
    Box,
    BuildPart,
    Color,
    Plane,
    Select,
    chamfer,
    fillet,
)

from bdbox import Choice, Int, Model, Preset


@dataclass
class DisplayColor:
    opacity: int = Int(default=0xFF, min=0x00, max=0xFF, step=1)
    color: str = Choice("default", ("lime", "default"))


class DemoModel(Model):
    width: float = 40.0
    length: float = 30.0
    height: float = 10.0
    chamfer: bool = True
    fillet: bool = True
    display_color: DisplayColor = field(default_factory=DisplayColor)
    presets = (
        Preset("thin", height=2.0, chamfer=False),
        Preset(
            "cube",
            width=30.0,
            length=30.0,
            height=30.0,
            chamfer=False,
            fillet=False,
        ),
        Preset("chamfer-cube", width=30.0, length=30.0, height=30.0),
        Preset(
            "lime-chamfer-cube",
            width=30.0,
            length=30.0,
            height=30.0,
            display_color=DisplayColor(color="lime"),
        ),
    )

    def build(self) -> Any:
        with BuildPart() as p:
            Box(self.width, self.length, self.height)
            if self.fillet:
                fillet(
                    p.edges(Select.LAST).filter_by(Axis.Z),
                    min(self.width, self.length) / 4,
                )
            if self.chamfer:
                chamfer(
                    p.edges().filter_by(Plane.XY),
                    min(min(self.width, self.length) / 8, self.height / 4),
                )
        color = 0xB0EB00 if (self.display_color.color == "lime") else 0xE8B024
        p.part.color = Color(color, alpha=self.display_color.opacity)
        return p.part
