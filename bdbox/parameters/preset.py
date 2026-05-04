"""Parameter system presets."""

from typing import Any


class Preset:
    """A saved combination of parameter values, applied by name.

    Instead of overriding multiple values for a common configuration,
    conveniently apply those values together using a preset.

    Args:
        name: Preset name.
        description: Optional human-readable description.
        **values: Parameter values to apply when this preset is selected.
    """

    def __init__(
        self, name: str, *, description: str | None = None, **values: Any
    ) -> None:
        self.name = name
        self.description = description
        self.values: dict[str, Any] = values

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "values": self.values,
        }
