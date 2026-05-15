"""STEP file export action."""

from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cached_property
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

import tyro

from bdbox.console import log
from bdbox.errors import InternalError, UsageError
from bdbox.geometry import resolve_geometry
from bdbox.parameters.model_state import model_state

from .action import ModelAction

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from build123d import Shape


@dataclass
class Exports:
    geometry: Shape
    model_name: str
    single: bool = False

    @cached_property
    def parts(self) -> dict[str, Shape]:
        export_parts = {self.model_name: self.geometry}
        if self.single or len(self.geometry.leaves) == 1:
            return export_parts
        for part in self.geometry.leaves:
            part_name = ".".join(
                [
                    self.model_name,
                    *[
                        self.labels.get(id(c), self._shape_label(c))
                        for c in part.path[1:]
                    ],
                ]
            )
            if part_name in export_parts:
                raise InternalError(f"Duplicate part name {part_name!r}")
            export_parts[part_name] = part
        return export_parts

    @cached_property
    def labels(self) -> dict[int, str]:
        """Map node IDs to deduplicated label names."""
        labels = {}

        def determine_labels(solid: object) -> None:
            if not (children := getattr(solid, "children", ())):
                return
            existing_labels = [self._shape_label(c) for c in children]
            assigned_labels = set(existing_labels)
            totals = Counter(existing_labels)
            seen_counts = defaultdict(count)
            max_tries = min(len(children) + 1, 100)
            for child, label in zip(children, existing_labels, strict=True):
                if totals[label] == 1 or (n := next(seen_counts[label])) == 0:
                    labels[id(child)] = label
                    continue
                for suffix_n in range(n + 1, n + 1 + max_tries):
                    candidate = f"{label}_{suffix_n:03d}"
                    if candidate not in assigned_labels:
                        labels[id(child)] = candidate
                        assigned_labels.add(candidate)
                        break
                else:
                    raise InternalError(
                        f"Unable to determine unique name for {label!r}"
                    )
            for child in children:
                determine_labels(child)

        determine_labels(self.geometry)
        return labels

    @staticmethod
    def _shape_label(node: object) -> str:
        return getattr(node, "label", None) or type(node).__name__


@dataclass
class ExportAction(ModelAction):
    """Export collected geometry to a STEP or STL file."""

    output: Annotated[
        Path,
        tyro.conf.Positional,
        tyro.conf.arg(metavar="DIR", help="Output directory."),
    ] = Path()

    single: Annotated[
        bool,
        tyro.conf.arg(
            aliases=["-s"],
            help=("Only create a single combined export file."),
            help_behavior_hint="(default: no)",
        ),
        tyro.conf.FlagCreatePairsOff,
    ] = field(default=False, kw_only=True)

    all_presets: Annotated[
        bool,
        tyro.conf.arg(
            aliases=["-a"],
            help=(
                "Export each preset to a separate file"
                " in the output directory."
            ),
            help_behavior_hint="(default: no)",
        ),
        tyro.conf.FlagCreatePairsOff,
    ] = field(default=False, kw_only=True)

    format: Annotated[
        Literal["step", "stl"],
        tyro.conf.arg(aliases=["-f"], help="Output format."),
    ] = "step"

    default: Annotated[
        bool,
        tyro.conf.arg(
            aliases=["-n"],
            help=("Include no-preset render with -a/--all-presets."),
            help_behavior_hint="(default: yes)",
        ),
        tyro.conf.FlagCreatePairsOff,
    ] = field(default=True, kw_only=True)

    @cached_property
    def _exporter(self) -> Callable[..., bool]:
        match self.format:
            case "step":
                from build123d import export_step  # noqa: PLC0415

                return export_step
            case "stl":
                from build123d import export_stl  # noqa: PLC0415

                return export_stl
        raise InternalError(f"Unknown format {self.format}")

    def __call__(self) -> None:
        """Export single render or all preset renders to a STEP or STL file."""
        if self.all_presets:
            return
        geometry = resolve_geometry()
        if not geometry:
            raise UsageError("No geometry to export")
        model_name = model_state.model_name()
        if model_state.model_cli and (preset := model_state.model_cli.preset):
            model_name += f"-{preset}"
        exports = Exports(geometry, model_name=model_name, single=self.single)
        self.output.mkdir(exist_ok=True, parents=True)
        for name, solid in exports.parts.items():
            part_file = self.output / f"{name}.{self.format}"
            log.info(f"Exporting model geometry to {part_file}")
            self._exporter(solid, str(part_file))

    def before_harness(
        self, args: ModelAction.ModelHarnessProtocol
    ) -> ModelAction.BeforeHarnessResult:
        if self.all_presets:
            runs = [
                (
                    [
                        str(args.model),
                        "export",
                        str(self.output),
                        *(("--preset", preset.name) if preset else ()),
                        *args.params_argv,
                    ],
                    ExportAction(
                        all_presets=False,
                        output=self.output,
                        single=self.single,
                        format=self.format,
                    ),
                )
                for preset in (
                    *((None,) if self.default else ()),
                    *getattr(args.model_params_cls, "presets", ()),
                )
            ]
            return ModelAction.HarnessResult(runs=runs)
        return None

    @contextmanager
    def on_model_render(self) -> Iterator[None]:
        if self.all_presets:
            self._ensure_runner()
        with super().on_model_render():
            yield
