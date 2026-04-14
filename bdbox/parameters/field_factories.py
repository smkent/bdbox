"""Parameter field factories.

Note:
    Model code only receives resolved parameter values at runtime (``float``,
    ``int``, etc.). The underlying ``Field`` classes are an implementation
    detail.

    When using a [``Params``][bdbox.parameters.parameters.Params] subclass,
    resolved values are accessible as class attributes (e.g. ``P.width``).
    When using a [``Model``][bdbox.model.Model] subclass, resolved values are
    accessible as instance attributes (e.g. ``self.width``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from .fields import (
    BoolField,
    ChoiceField,
    Field,
    FloatField,
    IntField,
    StrField,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

T = TypeVar("T")


@Field.as_dataclass_field
def Float(  # noqa: N802
    default: float,
    *,
    min: float | None = None,  # noqa: A002
    max: float | None = None,  # noqa: A002
    step: float | None = None,
    description: str | None = None,
) -> FloatField:
    """Declare a floating-point parameter.

    Args:
        default: Default value.
        min: Minimum allowed value (inclusive).
        max: Maximum allowed value (inclusive).
        step: Suggested increment for UI controls.
        description: Human-readable description.
    """
    return FloatField(
        default, min=min, max=max, step=step, description=description
    )


@Field.as_dataclass_field
def Int(  # noqa: N802
    default: int,
    *,
    min: int | None = None,  # noqa: A002
    max: int | None = None,  # noqa: A002
    step: int | None = None,
    description: str | None = None,
) -> IntField:
    """Declare an integer parameter.

    Args:
        default: Default value.
        min: Minimum allowed value (inclusive).
        max: Maximum allowed value (inclusive).
        step: Suggested increment for UI controls.
        description: Human-readable description.
    """
    return IntField(
        default, min=min, max=max, step=step, description=description
    )


@Field.as_dataclass_field
def Bool(  # noqa: N802
    default: bool,  # noqa: FBT001
    *,
    description: str | None = None,
) -> BoolField:
    """Declare a boolean parameter.

    Args:
        default: Default value.
        description: Human-readable description.
    """
    return BoolField(default, description=description)


@Field.as_dataclass_field
def Str(  # noqa: N802
    default: str,
    *,
    min_length: int | None = None,
    max_length: int | None = None,
    description: str | None = None,
) -> StrField:
    """Declare a string parameter.

    Args:
        default: Default value.
        min_length: Minimum allowed value length (inclusive).
        max_length: Maximum allowed value length (inclusive).
        description: Human-readable description.
    """
    return StrField(
        default,
        min_length=min_length,
        max_length=max_length,
        description=description,
    )


@Field.as_dataclass_field
def Choice(  # noqa: N802
    default: T, choices: Sequence[T], *, description: str | None = None
) -> ChoiceField[T]:
    """Declare a parameter for choosing from a fixed set of values.

    The value type is inferred from ``choices``.

    Args:
        default: Default value. Must be one of ``choices``.
        choices: Allowed values. All values must be the same type.
        description: Human-readable description.
    """
    return ChoiceField(default, choices, description=description)
