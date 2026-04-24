"""Parameter system field utilities."""

import sys
from collections.abc import Callable, Sequence
from dataclasses import Field as DCField
from dataclasses import dataclass, field
from functools import wraps
from typing import (
    Annotated,
    Any,
    ClassVar,
    Generic,
    Literal,
    ParamSpec,
    TypeVar,
)

import tyro
from annotated_types import Ge, Le, MaxLen, MinLen

from bdbox.errors import ParamsError, ParamValidationError

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

Number = TypeVar("Number", float, int)
P = ParamSpec("P")
T = TypeVar("T")


class Field:
    """Base class for parameter field types."""

    METADATA_KEY = "bdbox_field"

    value_type: ClassVar[type]
    default: Any
    description: str | None = None

    @staticmethod
    def as_dataclass_field(func: Callable[P, "Field"]) -> Callable[P, T]:
        """Decorator for creating `Field` instances as `dataclasses.Field`."""

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            new_field = func(*args, **kwargs)
            return field(
                default=new_field.default,
                metadata={Field.METADATA_KEY: new_field},
            )

        return wrapper

    @classmethod
    def from_dataclass_field(cls, field: DCField) -> Self | None:
        if isinstance(
            (ff := field.metadata.get(cls.METADATA_KEY, field.type)), Field
        ):
            return ff
        return None

    def annotation(self) -> Any:
        constraints = self.constraints()
        if not constraints:
            return self.value_type
        return Annotated[tuple([self.value_type, *constraints])]  # ty: ignore[invalid-type-form]  # noqa: C409

    def constraints(self) -> Sequence[object]:
        return [self._cli_conf(description=self.description)]

    def validate(self, value: Any) -> None:
        """Validate a value against this field's constraints."""

    def _cli_conf(
        self,
        *,
        min: float | None = None,  # noqa: A002
        max: float | None = None,  # noqa: A002
        step: float | None = None,
        description: str | None = None,
    ) -> object:
        arg_config = {}
        if description is not None:
            arg_config["help"] = description
        if min is not None or max is not None or step is not None:
            metavar = ""
            if min is not None:
                metavar += f"{min} <= "
            metavar += self.value_type.__name__.upper()
            if max is not None:
                metavar += f" <= {max}"
            if step is not None:
                metavar += f" ({step})"
            arg_config["metavar"] = metavar
        return tyro.conf.arg(**arg_config)

    def _validate_number(
        self,
        value_type: type,
        default: Number,
        min_val: float | None,
        max_val: float | None,
        step: float | None,
    ) -> Number:
        default = value_type(default)
        if min_val is not None and max_val is not None and min_val > max_val:
            raise ParamValidationError(
                f"min ({min_val!r}) must be <= max ({max_val!r})"
            )
        if min_val is not None and default < min_val:
            raise ParamValidationError(
                f"({default!r}) must be >= min ({min_val!r})"
            )
        if max_val is not None and default > max_val:
            raise ParamValidationError(
                f"({default!r}) must be <= max ({max_val!r})"
            )
        if step is not None and step <= 0:
            raise ParamValidationError(f"step ({step!r}) must be > 0")
        return default


class NumberField(Field):
    """Number parameter field base class."""

    default: int
    min: int | None = None
    max: int | None = None
    step: int | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        try:
            self.default = self._validate_number(
                self.value_type, self.default, self.min, self.max, self.step
            )
        except ParamValidationError as exc:
            raise ParamsError(str(exc)) from exc

    def constraints(self) -> Sequence[object]:
        conf = self._cli_conf(
            min=self.min,
            max=self.max,
            step=self.step,
            description=self.description,
        )
        return [
            *([] if self.min is None else [Ge(self.min)]),
            *([] if self.max is None else [Le(self.max)]),
            conf,
        ]

    def validate(self, value: Any) -> None:
        self._validate_number(float, value, self.min, self.max, None)


@dataclass
class FloatField(NumberField):
    """Floating-point parameter."""

    value_type: ClassVar[type] = float
    default: float
    min: float | None = None
    max: float | None = None
    step: float | None = None
    description: str | None = None


@dataclass
class IntField(NumberField):
    """Integer parameter."""

    value_type: ClassVar[type] = int
    default: int
    min: int | None = None
    max: int | None = None
    step: int | None = None
    description: str | None = None


@dataclass
class BoolField(Field):
    """Boolean parameter."""

    value_type: ClassVar[type] = bool
    default: bool
    description: str | None = None


@dataclass
class StrField(Field):
    """String parameter."""

    value_type: ClassVar[type] = str
    default: str
    min_length: int | None = None
    max_length: int | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        try:
            self._validate_number(
                int,
                len(self.default),
                self.min_length,
                self.max_length,
                step=None,
            )
        except ParamValidationError as exc:
            raise ParamsError(str(exc)) from exc

    def constraints(self) -> Sequence[object]:
        return [
            *([] if self.min_length is None else [MinLen(self.min_length)]),
            *([] if self.max_length is None else [MaxLen(self.max_length)]),
            self._cli_conf(description=self.description),
        ]

    def validate(self, value: Any) -> None:
        """Validate a value against this field's constraints."""
        value = str(value)
        self._validate_number(
            int, len(value), self.min_length, self.max_length, step=None
        )


@dataclass
class ChoiceField(Field, Generic[T]):
    """Choice parameter with a fixed set of choices."""

    value_type: ClassVar[type] = Sequence[T]
    default: T
    choices: Sequence[T]
    description: str | None = None

    def __post_init__(self) -> None:
        if self.choices:
            first_type = type(self.choices[0])
            for item in self.choices[1:]:
                if type(item) is not first_type:
                    raise ParamsError(
                        f"All choices must be the same type;"
                        f" got {first_type.__name__!r}"
                        f" and {type(item).__name__!r}"
                    )
        if self.default not in self.choices:
            raise ParamsError(
                f"Choice default {self.default!r}"
                f" is not in choices {self.choices!r}"
            )

    def annotation(self) -> Any:
        constraints = self.constraints()
        if not constraints:
            return Literal[tuple(self.choices)]  # ty: ignore[invalid-type-form]
        return Annotated[(Literal[tuple(self.choices)], *constraints)]  # ty: ignore[invalid-type-form]

    def validate(self, value: Any) -> None:
        if value not in self.choices:
            raise ParamValidationError(
                f"Value {value!r} is not in choices {self.choices!r}"
            )
