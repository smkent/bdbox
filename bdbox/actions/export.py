"""STEP file export action."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Annotated, Literal

import tyro

from bdbox.errors import Error
from bdbox.geometry import resolve_geometry

from .action import ModelAction

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


@dataclass
class ExportAction(ModelAction):
    """Export collected geometry to a STEP or STL file."""

    output: Annotated[
        Path,
        tyro.conf.Positional,
        tyro.conf.arg(
            metavar="output-path",
            help=(
                "Output file path (single mode)"
                " or directory (with --all-presets)."
            ),
        ),
    ]

    all_presets: Annotated[
        bool,
        tyro.conf.arg(
            aliases=["-a"],
            help=(
                "Export each preset to a separate file"
                " in the output directory."
            ),
        ),
    ] = field(default=False, kw_only=True)

    format: Annotated[
        Literal["step", "stl"],
        tyro.conf.arg(help="-a/--all-presets output format."),
    ] = "step"

    default: Annotated[
        bool,
        tyro.conf.arg(
            aliases=["-n"],
            help=("Include no-preset render with -a/--all-presets."),
        ),
        tyro.conf.FlagCreatePairsOff,
    ] = field(default=True, kw_only=True)

    @property
    def _exporter(self) -> Callable[..., bool]:
        match self.output.suffix.lower():
            case ".step":
                from build123d import export_step  # noqa: PLC0415

                return export_step
            case ".stl":
                from build123d import export_stl  # noqa: PLC0415

                return export_stl
        raise Error(f"Unknown file type {self.output.suffix}")

    def __call__(self) -> None:
        """Export single render or all preset renders to a STEP or STL file."""
        if self.all_presets:
            return
        geometry = resolve_geometry()
        if not geometry:
            raise Error("No geometry to export")
        print(f"Exporting model geometry to {self.output}")  # noqa: T201
        self._exporter(geometry, str(self.output))

    def before_harness(
        self, args: ModelAction.ModelHarnessProtocol
    ) -> ModelAction.BeforeHarnessResult:
        if self.all_presets:
            runs = []
            for preset in (
                *((None,) if self.default else ()),
                *getattr(args.model_params_cls, "presets", ()),
            ):
                name = preset.name if preset else "default"
                dest = self.output / f"{name}.{self.format}"
                runs.append(
                    (
                        [
                            str(args.model),
                            "export",
                            str(dest),
                            *(("--preset", preset.name) if preset else ()),
                            *args.params_argv,
                        ],
                        ExportAction(
                            all_presets=False,
                            output=dest,
                            format=self.format,
                        ),
                    )
                )
            self.output.mkdir(parents=True, exist_ok=True)
            return ModelAction.HarnessResult(runs=runs)
        return None

    @contextmanager
    def on_model_render(self) -> Iterator[None]:
        if self.all_presets:
            self._ensure_runner()
        yield
