from __future__ import annotations

from dataclasses import dataclass, field

from bdbox import Params, Preset


@dataclass
class SubOptions:
    several: list[int] = field(default_factory=list)


class P(Params):
    sub_options: SubOptions
    width: float = 5.0

    presets = (
        Preset(
            "custom", width=50.0, sub_options=SubOptions(several=[1138, 2187])
        ),
    )
