from dataclasses import Field as DCField
from dataclasses import dataclass, field, fields, is_dataclass
from functools import cached_property
from typing import ClassVar, Literal

from bdbox.errors import ParamsError

from .fields import Field
from .preset import Preset


@dataclass
class Annotater:
    params_class: type
    seen: set = field(default_factory=set, init=False)

    def __call__(self) -> None:
        sub_cls = self.params_class
        annotations = getattr(sub_cls, "__annotations__", {}).copy()
        for name, value in sub_cls.__dict__.items():
            if (
                (name.startswith("__") and name.endswith("__"))
                or name in annotations
                or name == "presets"
                or callable(value)
                or isinstance(value, (classmethod, property, cached_property))
            ):
                continue

            basic_types = {float, int, bool, str}
            if (value_type := type(value)) in basic_types:
                # Attach a generic annotation so @dataclass picks it up
                annotations[name] = value_type
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

        preset_list = sub_cls.__dict__.get("presets", ())
        for preset in preset_list:
            if not isinstance(preset, Preset):
                raise ParamsError(
                    f"presets item must be a Preset instance,"
                    f" got {type(preset).__name__}"
                )

            for key in preset.values:
                if key not in sub_cls.__dict__ and key not in annotations:
                    raise ParamsError(
                        f"Preset {preset.name!r}"
                        f" references unknown field {key!r}"
                    )

        if preset_list:
            preset_names = tuple(p.name for p in preset_list)
            annotations["preset"] = Literal[preset_names] | None  # ty: ignore[invalid-type-form]
            sub_cls.preset = field(default=None, kw_only=True)  # ty: ignore[unresolved-attribute]
        else:
            annotations["preset"] = ClassVar[str | None]
            sub_cls.preset = None  # ty: ignore[unresolved-attribute]

        # Apply annotations in original attribute order
        sub_cls.__annotations__ = {
            name: annotation
            for name in [
                *[k for k in annotations if k not in sub_cls.__dict__],
                *sub_cls.__dict__,
            ]
            if (annotation := annotations.get(name))
        }
        dataclass(sub_cls)
        for f in fields(sub_cls):
            if is_dataclass(f.type):
                self.annotate_nested_dataclass_fields(f.type)

    def annotate_nested_dataclass_fields(self, dc_cls: type | object) -> None:
        if not is_dataclass(dc_cls) or dc_cls in self.seen:
            return
        self.seen.add(dc_cls)
        if not hasattr(dc_cls, "__annotations__"):
            dc_cls.__annotations__ = {}
        for f in fields(dc_cls):
            if is_dataclass(f.type):
                self.annotate_nested_dataclass_fields(f.type)
                continue
            if bdfield := Field.from_dataclass_field(f):
                field_type = bdfield.annotation()
                dc_cls.__annotations__[f.name] = field_type
                f.type = field_type
