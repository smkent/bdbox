"""Parameter system utilities."""

import atexit
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, ClassVar

from bdbox.actions.action import Action
from bdbox.actions.run import RunAction
from bdbox.cli import CLI
from bdbox.errors import ParamsError
from bdbox.geometry import Geometry

from .annotations import Annotater
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
    filename: str | None = None
    model_subclasses: list[Any] = field(default_factory=list)
    action: Action = field(default_factory=RunAction)


class ParamsType(type):
    @staticmethod
    def __in_pkg(mro: type, pkg: str) -> bool:
        return (n := mro.__module__) == pkg or n.startswith(f"{pkg}.")

    def __base_class(cls, pkg: str) -> str | None:
        for mro in cls.__mro__[1:]:
            if cls.__in_pkg(mro, pkg):
                return mro.__name__
        return None

    def __repr__(cls) -> str:
        if cls.__in_pkg(
            cls, (pkg := (__package__ or "").split(".", 1)[0])
        ) or not (pkgname := cls.__base_class(pkg)):
            return super().__repr__()
        kvlist = [
            f"{f.name}={getattr(cls, f.name, '(required)')!r}"
            for f in fields(cls)
        ]
        return f"{cls.__qualname__}({pkgname})({', '.join(kvlist)})"


@dataclass_transform(field_specifiers=(Float, Int, Bool, Str, Choice))
@dataclass
class Params(CLI, metaclass=ParamsType):
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
        Annotater(cls)()

        if cls.__module__ == "__main__":
            Geometry.ensure_params_class_mode()
            if Params._main_info.model_subclasses:
                raise ParamsError(
                    f"Cannot define Params subclass {cls.__name__!r}:"
                    " a Params subclass is already defined in this script"
                )
            Params._main_info.model_subclasses.append(cls)
            cli_result = cls.cli_config().instance_from_cli(
                prog=Path(sys.argv[0]).name
            )
            for f in fields(cls):
                setattr(cls, f.name, getattr(cli_result.params, f.name))
            Params._main_info.action = cli_result.action
            atexit.register(Params._atexit_handler)

    @classmethod
    def _atexit_handler(cls) -> None:
        atexit.unregister(Params._atexit_handler)
        if Params._main_info.model_subclasses:
            Params._main_info.action()

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

        def validate_dc(instance: object) -> None:
            if not is_dataclass(instance):
                return
            for f in fields(instance):
                value = getattr(instance, f.name)
                if is_dataclass(value):
                    validate_dc(value)
                if ff := Field.from_dataclass_field(f):
                    ff.validate(value)

        validate_dc(self)

    @classmethod
    def _init_this_subclass(cls) -> bool:
        return True
