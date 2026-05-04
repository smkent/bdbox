"""Model utilities."""

from __future__ import annotations

import atexit
import os
import sys
import traceback
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, TypeAlias

from .errors import MultipleModelsError
from .geometry import show
from .parameters.annotations import Annotater
from .parameters.fields import Field
from .parameters.parameters import Params
from .parameters.state import run_state

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
        run_state.ensure_module_filename(cls)
        cli_result = cls.cli_config().instance_from_cli(prog=cls.__name__)
        run_state.resolved_values = {
            f.name: getattr(cli_result.params, f.name)
            for f in fields(cli_result.params)
            if Field.from_dataclass_field(f)
        }
        show(cli_result.params.build())
        with cli_result.action.on_model_render():
            run_state.act_once(cli_result.action)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        object.__init_subclass__(**kwargs)
        Annotater(cls)()

        if run_state.is_class_in_main(cls):
            run_state.ensure_mode(
                run_state.Mode.MODEL_CLASS,
                f"Cannot define Model subclass {cls!r}"
                " with an existing Params subclass",
            )
            if not run_state.model_subclasses:
                atexit.register(Model._atexit_handler)
                run_state.filename = getattr(
                    sys.modules.get(cls.__module__), "__file__", None
                )
            run_state.model_subclasses.append(cls)

    @classmethod
    def _init_this_subclass(cls) -> bool:
        return cls.__mro__[1] is not Params

    @classmethod
    def _atexit_handler(cls) -> None:
        try:
            if not (model_class := run_state.get_model()):
                return
        except MultipleModelsError as e:
            print(  # noqa: T201
                f"Multiple Model subclasses defined: {', '.join(e.names)}."
                " Call .run() explicitly.",
                file=sys.stderr,
            )
            return
        try:
            model_class.run()
        except BaseException as exc:  # noqa: BLE001
            if not isinstance(exc, SystemExit):
                traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
            code = exc.code if isinstance(exc, SystemExit) else 1
            os._exit(code if isinstance(code, int) else 1)
