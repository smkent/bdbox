"""Parameter system utilities."""

import atexit
import sys
from collections.abc import Sequence
from dataclasses import Field as DCField
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, ClassVar, Literal

import tyro

from bdbox.errors import ParamsError
from bdbox.geometry import GeometryMode, resolve_geometry

from .field_factories import Bool, Choice, Float, Int, Str
from .fields import Field
from .preset import Preset

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if sys.version_info >= (3, 12):
    from typing import dataclass_transform
else:
    from typing_extensions import dataclass_transform


@dataclass
class _MainInfo:
    params_defined: bool = False
    filename: str | None = None
    model_subclasses: list[Any] = field(default_factory=list)


@dataclass_transform(field_specifiers=(Float, Int, Bool, Str, Choice))
@dataclass
class Params:
    """Base class for script-style single models with parameters.

    Declare parameters as class attributes in the same form as
    [dataclass][dataclasses.dataclass] fields with any of:

    * Standard type annotations (`int`, `float`, `bool`, etc.)
    * Default value (unannotated attributes infer types from default values)
    * [Field factory functions](fields.md) provided for creating fields
      with constraints
    * [``dataclasses.field``][dataclasses.field] same as any other
      [dataclass][dataclasses.dataclass]

    When run directly as a script, CLI arguments are parsed automatically at
    class definition time, and resolved parameter values are accessible as
    class attributes. A handler is registered to retrieve the rendered model
    using [``show``][bdbox.geometry.show] when the script completes, if not
    manually called.

    A ``presets`` class attribute may declare a selection of
    [``Preset``][bdbox.parameters.preset.Preset] objects.

    !!! Note

        Subclasses are created as [dataclasses][dataclasses] automatically.
        Do not decorate subclasses with `@dataclass`.

    Example:
        ```python
        class P(Params):
            width = Float(40.0, min=10, max=100)
            thickness = Float(3.0, min=1, max=10)

            presets = (Preset("small", width=15.0, thickness=2.0),)

        result = Box(P.width, P.width, P.thickness)
        ```
    """

    _main_info: ClassVar[_MainInfo] = _MainInfo()
    preset: str | None = field(default=None, kw_only=True)
    presets: ClassVar[Sequence[Preset]] = ()

    @classmethod
    def with_preset(cls, preset: str, **overrides: Any) -> Self:
        """Create a new instance with values from a preset applied.

        Args:
            preset: Name of the preset to apply.
            **overrides: Additional field values to apply after the preset.
        """
        return cls(preset=preset, **overrides)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls._init_this_subclass():
            return
        cls._annotate_as_dataclass()

        if cls.__module__ == "__main__":
            GeometryMode.ensure_params_class_mode()
            if Params._main_info.params_defined:
                raise ParamsError(
                    f"Cannot define Params subclass {cls.__name__!r}:"
                    " a Params subclass is already defined in this script"
                )
            Params._main_info.params_defined = True
            instance = tyro.cli(cls, prog=Path(sys.argv[0]).name)
            for f in cls._get_dataclass_fields():
                setattr(cls, f.name, getattr(instance, f.name))
            atexit.register(resolve_geometry)

    def __post_init__(self) -> None:
        if self.preset:
            preset_map = {p.name: p for p in self.presets}
            if self.preset not in preset_map:
                raise ParamsError(f"Unknown preset {self.preset!r}")
            preset = preset_map[self.preset]
            dc_fields = self.__class__.__dataclass_fields__
            for name, value in preset.values.items():
                if getattr(self, name) == dc_fields[name].default:
                    setattr(self, name, value)
        for f in self._get_dataclass_fields():
            if ff := Field.from_dataclass_field(f):
                ff.validate(getattr(self, f.name))

    @classmethod
    def _init_this_subclass(cls) -> bool:
        return True

    @classmethod
    def _annotate_as_dataclass(cls: type) -> None:
        annotations = getattr(cls, "__annotations__", {}).copy()
        for name, value in cls.__dict__.items():
            if (
                (name.startswith("__") and name.endswith("__"))
                or name in annotations
                or name == "presets"
                or callable(value)  # Skip methods
            ):
                continue

            basic_types = {float, int, bool, str}
            if (value_type := type(value)) in basic_types:
                # Attach a generic annotation so @dataclass picks it up
                annotations[name] = value_type.__name__
                continue

            if isinstance(value, DCField):
                if bdfield := Field.from_dataclass_field(value):
                    annotations[name] = bdfield.annotation()
                else:
                    annotations[name] = type(value.default)
                continue

            raise ParamsError(
                f"Unknown {name} type {type(value)} must be a dataclass field"
            )

        preset_list = cls.__dict__.get("presets", ())
        for preset in preset_list:
            if not isinstance(preset, Preset):
                raise ParamsError(
                    f"presets item must be a Preset instance,"
                    f" got {type(preset).__name__}"
                )

            for key in preset.values:
                if key not in cls.__dict__ and key not in annotations:
                    raise ParamsError(
                        f"Preset {preset.name!r}"
                        f" references unknown field {key!r}"
                    )

        if preset_list:
            preset_names = tuple(p.name for p in preset_list)
            annotations["preset"] = Literal[preset_names] | None  # ty: ignore[invalid-type-form]
            cls.preset = field(default=None, kw_only=True)  # ty: ignore[unresolved-attribute]
        else:
            annotations["preset"] = ClassVar[str | None]
            cls.preset = None  # ty: ignore[unresolved-attribute]
        # Apply annotations in original attribute order
        cls.__annotations__ = {
            name: annotation
            for name in [
                *[k for k in annotations if k not in cls.__dict__],
                *cls.__dict__,
            ]
            if (annotation := annotations.get(name))
        }
        dataclass(cls)

    @classmethod
    def _get_dataclass_fields(cls) -> Sequence[DCField]:
        return [f for f in fields(cls) if f.name != "preset"]
