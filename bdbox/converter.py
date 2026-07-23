"""Shared cattrs conveniences."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import (
    TYPE_CHECKING,
    Annotated,
    get_args,
    get_origin,
    get_type_hints,
)

import cattrs
from cattrs.gen import (
    AttributeOverride,
    make_dict_structure_fn,
    make_dict_unstructure_fn,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


class Converter(cattrs.Converter):
    """A ``cattrs.Converter`` with PEP 563 ``override`` annotations support.

    cattrs.Converter's override auto-detection re-resolves PEP 563 annotations
    via ``get_type_hints(cl)`` without ``include_extras=True``, which
    silently discards any ``override`` metadata on field types.
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_hooks()

    def register_hooks(self) -> None:
        self.register_structure_hook_factory(
            is_dataclass,
            lambda target: make_dict_structure_fn(
                target,
                self,
                **self.get_type_hints(target),  # ty: ignore[invalid-argument-type]
            ),
        )
        self.register_unstructure_hook_factory(
            is_dataclass,
            lambda target: make_dict_unstructure_fn(
                target,
                self,
                **self.get_type_hints(target),  # ty: ignore[invalid-argument-type]
            ),
        )

    @staticmethod
    def get_type_hints(
        target: type[DataclassInstance],
    ) -> dict[str, AttributeOverride]:
        try:
            hints = get_type_hints(target, include_extras=True)
        except NameError:
            return {}
        overrides: dict[str, AttributeOverride] = {}
        for f in fields(target):
            hint = hints.get(f.name)
            if get_origin(hint) is not Annotated:
                continue
            for extra in get_args(hint)[1:]:
                if isinstance(extra, AttributeOverride):
                    overrides[f.name] = extra
                    break
        return overrides
