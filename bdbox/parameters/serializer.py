"""Parameter schema generation."""

from __future__ import annotations

import types as _types
from collections import abc
from contextlib import suppress
from dataclasses import MISSING, dataclass, field, fields, is_dataclass
from dataclasses import Field as DCField
from enum import Enum
from typing import (
    Annotated,
    Any,
    Literal,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from cattrs import Converter

from .fields import Field

_UNION_ORIGINS: frozenset[Any] = frozenset({Union, _types.UnionType})


@dataclass
class Serializer:
    _EXCLUDED = frozenset({"preset"})

    converter: Converter = field(default_factory=Converter)

    def __post_init__(self) -> None:
        def _hook(obj: Any) -> Any:
            return {
                f.name: self.unstructure(getattr(obj, f.name))
                for f in fields(obj)
            }

        self.converter.register_unstructure_hook_func(is_dataclass, _hook)

    def get_type_hints(self, target: Any) -> dict[str, Any]:
        def _localns(
            cls: type, in_ns: dict[str, type] | None = None
        ) -> dict[str, Any]:
            ns: dict[str, type] = in_ns or cast(
                "dict[str, type]",
                {
                    "Mapping": abc.Mapping,
                    "MutableMapping": abc.MutableMapping,
                    "MutableSequence": abc.MutableSequence,
                    "MutableSet": abc.MutableSet,
                    "Sequence": abc.Sequence,
                    "Set": abc.Set,
                },
            )
            if issubclass(cls, Enum):
                ns.setdefault(cls.__name__, cls)
            if not is_dataclass(cls):
                return {}
            ns.setdefault(cls.__name__, cls)
            for f in fields(cls):
                if f.name in ns:
                    continue
                if ft := self._field_type(f):
                    _localns(ft, ns)
            return ns

        with suppress(NameError):
            return get_type_hints(
                target, include_extras=True, localns=_localns(target)
            )
        return {}

    def structure(self, value: Any, hint: type | None) -> Any:
        if hint is None:
            return value
        try:
            return self.converter.structure(value, hint)
        except NameError:
            if is_dataclass(hint) and isinstance(value, dict):
                self._register_fallback_hook(hint)
                return self.converter.structure(value, hint)
            raise

    def _field_type(self, f: DCField) -> type | None:
        if (df := f.default_factory) is not MISSING and (
            isinstance(df, type)
            or (
                callable(df)
                and isinstance((df := getattr(df(), "__class__", None)), type)
            )
        ):
            return df
        return type(f.default) if (f.default not in (MISSING, None)) else None

    def _register_fallback_hook(self, cls: type) -> None:
        hints = self.get_type_hints(cls)

        def _hook(obj: Any, t: type) -> Any:
            if not isinstance(obj, dict):
                return obj
            return t(
                **{
                    f.name: (
                        self.structure(obj[f.name], ftype)
                        if (
                            ftype := (hints.get(f.name) or self._field_type(f))
                        )
                        else obj[f.name]
                    )
                    for f in fields(t)
                    if f.name in obj
                }
            )

        self.converter.register_structure_hook(cls, _hook)

    def unstructure(self, value: Any, hint: type | None = None) -> Any:
        try:
            return self.converter.unstructure(value, unstructure_as=hint)
        except NameError:
            cls = type(value)
            if is_dataclass(cls):
                self._register_fallback_unstructure_hook(cls)
                return self.converter.unstructure(value, unstructure_as=hint)
            raise

    def _register_fallback_unstructure_hook(self, cls: type) -> None:
        def _hook(obj: Any) -> Any:
            return {
                f.name: self.unstructure(getattr(obj, f.name))
                for f in fields(obj)
            }

        self.converter.register_unstructure_hook(cls, _hook)

    def generate(self, cls: type) -> dict:
        hints = self.get_type_hints(cls)
        field_schemas = {}
        for f in fields(cls):
            if f.name in self._EXCLUDED:
                continue
            if not (hint := hints.get(f.name)):
                continue
            field_schemas[f.name] = self._field_schema(f, hint)
        return {
            "type": "object",
            "properties": field_schemas,
            "required": sorted(field_schemas.keys()),
            "x-presets": [p.to_schema() for p in getattr(cls, "presets", ())],
        }

    def _field_schema(self, f: DCField, hint: Any) -> dict:
        """Generate schema for a field."""
        if ff := Field.from_dataclass_field(f):
            return ff.to_schema(self._hint_to_schema)

        default: Any = MISSING
        if f.default is not MISSING:
            default = f.default
        elif f.default_factory is not MISSING:  # type: ignore[misc]
            default = f.default_factory()

        return self._hint_to_schema(hint, default)

    def _hint_to_schema(
        self, hint: Any, default: Any = MISSING
    ) -> dict[str, Any]:
        """Generate schema from a type hint."""
        origin = get_origin(hint)
        args = get_args(hint)

        if origin is Annotated:
            return self._hint_to_schema(args[0], default)

        schema = {}
        if default is not MISSING:
            schema["default"] = self.unstructure(default)

        if origin in _UNION_ORIGINS:
            return schema | {"oneOf": [self._hint_to_schema(a) for a in args]}

        if origin is Literal:
            return schema | {"enum": list(args)}

        with suppress(TypeError):
            if isinstance(hint, type) and issubclass(hint, Enum):
                return (
                    schema
                    | {"enum": [e.value for e in hint]}
                    | self._hint_to_schema(type(next(iter(hint)).value))
                )

        if is_dataclass(hint):
            return schema | self._dataclass_to_schema(hint)

        if origin in (
            list,
            tuple,
            abc.Sequence,
            abc.MutableSequence,
            abc.Set,
            abc.MutableSet,
        ):
            schema |= {"type": "array"}
            if args:
                schema["items"] = self._hint_to_schema(args[0])
            return schema

        if origin in (dict, abc.Mapping, abc.MutableMapping):
            return schema | {"type": "object"}

        _primitives = {
            float: "number",
            int: "number",
            bool: "boolean",
            str: "string",
            type(None): "null",
        }
        if hint is bool:
            schema |= {"x-format": "checkbox"}
        if hint in _primitives:
            return schema | {"type": _primitives[hint]}
        raise TypeError(hint)

    def _dataclass_to_schema(self, cls: type) -> dict[str, Any]:
        hints = self.get_type_hints(cls)
        field_schemas = {}
        for f in fields(cls):
            if f.name in self._EXCLUDED:
                continue
            if not (hint := hints.get(f.name)):
                continue
            field_schemas[f.name] = self._field_schema(f, hint)

        return {
            "type": "object",
            "properties": field_schemas,
            "required": sorted(field_schemas.keys()),
        }
