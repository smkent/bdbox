from __future__ import annotations

from dataclasses import dataclass, field

from bdbox import Float, Inches, Int, Params, Preset


@dataclass
class Color:
    code: str = "ffffff"
    alpha: int = Int(default=255, min=0, max=255)


@dataclass
class SubOptions:
    color: Color
    first: int = field(default=1)
    several: list[int] = field(default_factory=list)


class P(Params):
    sub_options: SubOptions
    width = Float(10.0, min=1.0, max=100.0)
    length = Inches(5.0, min=2.0)
    height: float = 20.0

    presets = (
        Preset(
            "custom",
            width=50.0,
            length=50.0,
            height=50.0,
            sub_options=SubOptions(
                color=Color(), first=3, several=[1138, 2187]
            ),
        ),
    )
