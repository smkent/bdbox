"""Model utilities."""

from __future__ import annotations

import atexit
import os
import sys
import traceback
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeAlias

from .geometry import Geometry, show
from .parameters.annotations import Annotater
from .parameters.parameters import Params

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from build123d import Shape


@dataclass(init=False)
class Model(Params):
    """Base class for reusable models with parameters.

    Declare parameters as class attributes in the same form as
    [dataclass][dataclasses.dataclass] fields with any of:

    * Standard type annotations (`int`, `float`, `bool`, etc.)
    * Default value (unannotated attributes infer types from default values)
    * [Field factory functions](fields.md) provided for creating fields
      with constraints
    * [``dataclasses.field``][dataclasses.field] same as any other
      [dataclass][dataclasses.dataclass]

    CLI arguments are parsed within [``run``][bdbox.model.Model.run]. A handler
    is registered to invoke `run` if not called manually and only one `Model`
    subclass is defined.

    A ``presets`` class attribute may declare a selection of
    [``Preset``][bdbox.parameters.preset.Preset] objects.

    Implement [``build``][bdbox.model.Model.build] to construct and return
    model geometry. Access parameter values as instance attributes.

    !!! Note

        Subclasses are created as [dataclasses][dataclasses] automatically.
        Do not decorate subclasses with `@dataclass`.

    Example:
        ```python
        class MyModel(Model):
            width = Float(40.0, min=10, max=100)
            thickness = Float(3.0, min=1, max=10)

            presets = (Preset("small", width=15.0, thickness=2.0),)

            def build(self):
                return Box(self.width, self.width, self.thickness)
        ```
    """

    if TYPE_CHECKING:
        Build: TypeAlias = "Shape | Sequence[Shape] | Mapping[str, Shape]"

    def build(self) -> Model.Build:
        """Build and return model geometry.

        Info:
            Override this method in your subclass with your model code.

        Tip:
            Access resolved parameter values via instance attributes (e.g.
            ``self.width`` would be the resolved value for a parameter called
            ``width``).
        """
        raise NotImplementedError

    @classmethod
    def run(cls) -> None:
        """Parse CLI arguments, build the model, and retrieve geometry.

        Calls [``build``][bdbox.model.Model.build] with the resolved
        parameter values and passes the result to
        [``show``][bdbox.geometry.show].

        Info:
            Call this to build and use your model geometry.

        Note:
            If ``run`` is not called explicitly, and a single
            [``Model``][bdbox.model.Model] subclass is defined in
            [``__main__``][__main__], ``run`` will be called automatically when
            Python finishes.
        """
        atexit.unregister(Model._atexit_handler)
        if (
            Model._main_info.is_class_in_main(cls)
            and (mm := sys.modules.get(cls.__module__))
            and getattr(mm, "__file__", None)
            and Model._main_info.filename
        ):
            mm.__file__ = Model._main_info.filename
        cli_result = cls.cli_config().instance_from_cli(prog=cls.__name__)
        show(cli_result.params.build())
        cli_result.action()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        object.__init_subclass__(**kwargs)
        Annotater(cls)()

        if Model._main_info.is_class_in_main(cls):
            Geometry.ensure_model_class_mode(cls.__name__)
            if not Model._main_info.model_subclasses:
                atexit.register(Model._atexit_handler)
                Model._main_info.filename = getattr(
                    sys.modules.get(cls.__module__), "__file__", None
                )
            Model._main_info.model_subclasses.append(cls)

    @classmethod
    def _init_this_subclass(cls) -> bool:
        return cls.__mro__[1] is not Params

    @classmethod
    def _atexit_handler(cls) -> None:
        if not (model_subclasses := Model._main_info.model_subclasses):
            return
        if len(model_subclasses) > 1:
            names = ", ".join(c.__name__ for c in model_subclasses)
            print(  # noqa: T201
                f"Multiple Model subclasses defined: {names}."
                " Call .run() explicitly.",
                file=sys.stderr,
            )
            return
        try:
            model_subclasses[0].run()
        except BaseException as exc:  # noqa: BLE001
            if not isinstance(exc, SystemExit):
                traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
            code = exc.code if isinstance(exc, SystemExit) else 1
            os._exit(code if isinstance(code, int) else 1)
