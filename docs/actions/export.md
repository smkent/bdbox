---
title: Export
icon: lucide/download
---

# Export

The `export` action collects all geometry produced by the model and exports to
output file(s). A file containing the full model geometry is exported. If the
model contains multiple solids, an export file for each solid is also created.

## Usage

The output destination is a directory, created automatically if it doesn't
exist. The current directory is used when no directory is specified:

=== "`bdbox` with **file**"

    ```sh
    bdbox model.py export            # Export to current directory
    bdbox model.py export output/    # Export to output/ directory
    bdbox model.py export -f stl     # Export as STL
    ```

=== "`bdbox` with **module**"

    ```sh
    bdbox mypackage.mymodule export            # Export to current directory
    bdbox mypackage.mymodule export output/    # Export to output/ directory
    bdbox mypackage.mymodule export -f stl     # Export as STL
    ```

=== "Direct with **file**"

    ```sh
    python model.py export            # Export to current directory
    python model.py export output/    # Export to output/ directory
    python model.py export -f stl     # Export as STL
    ```

=== "Direct with **module**"

    ```sh
    python -m mypackage.mymodule export            # Export to current directory
    python -m mypackage.mymodule export output/    # Export to output/ directory
    python -m mypackage.mymodule export -f stl     # Export as STL
    ```

## Output format

| Flag | Format |
|---|---|
| `-f step` / `--format step` (default) | [STEP][step] (Standard for the Exchange of Product model data) |
| `-f stl` / `--format stl` | [STL][stl] (stereolithography) |

## Export files

Export file names are based on **[`Model`][bdbox.model.Model]** subclass names,
or model file/module names for other types of models, along with the current
[preset](../parameters/presets.md) name if one is selected.

When a model's geometry contains multiple solids, individual files for each
solid are also created. Files for individual solids are named with the
hierarchical path of the solid within the overall model, with suffixes attached
to duplicate names.

An example set of exported files is:

```
output/
├── mymodel.step
├── mymodel.body.Part.step
├── mymodel.body.Part_002.step
└── mymodel.addon.Part.step
```

Creation of export files for each individual solid can be disabled with the
`-s`/`--single` option.

## Combining with parameter flags

[Parameter flags](../parameters/cli.md) may appear before or after the
subcommand:

=== "`bdbox` with **file**"

    ```sh
    bdbox model.py --width 50 export
    bdbox model.py export --width 50
    ```

=== "`bdbox` with **module**"

    ```sh
    bdbox mypackage.mymodule --width 50 export
    bdbox mypackage.mymodule export --width 50
    ```

=== "Direct with **file**"

    ```sh
    python model.py --width 50 export
    python model.py export --width 50
    ```

=== "Direct with **module**"

    ```sh
    python -m mypackage.mymodule --width 50 export
    python -m mypackage.mymodule export --width 50
    ```

## Exporting all presets

Models can be rendered for all [presets](../parameters/presets.md) and exported
using the `-a`/`--all-presets` option. Each preset render produces files in the
output directory with the preset name appended to the base name (e.g.,
`mymodel-large.step`). A render with default parameter values is also created.
Use `-n`/`--no-default` to suppress the default render.

For a model named `mymodel` with presets `small` and `large`:

```
output/
├── mymodel.step
├── mymodel-large.step
└── mymodel-small.step
```

When the model produces multiple solids, per-solid files are also created for
each render.

=== "`bdbox` with **file**"

    ```sh
    bdbox model.py export output/ --all-presets    # STEP (default)
    bdbox model.py export output/ -a --format stl  # STL
    bdbox model.py export output/ -a --no-default  # Skip default render
    ```

=== "`bdbox` with **module**"

    ```sh
    bdbox mypackage.mymodule export output/ --all-presets    # STEP (default)
    bdbox mypackage.mymodule export output/ -a --format stl  # STL
    bdbox mypackage.mymodule export output/ -a --no-default  # Skip default render
    ```

=== "Direct with **file**"

    ```sh
    python model.py export output/ --all-presets    # STEP (default)
    python model.py export output/ -a --format stl  # STL
    python model.py export output/ -a --no-default  # Skip default render
    ```

=== "Direct with **module**"

    ```sh
    python -m mypackage.mymodule export output/ --all-presets    # STEP (default)
    python -m mypackage.mymodule export output/ -a --format stl  # STL
    python -m mypackage.mymodule export output/ -a --no-default  # Skip default render
    ```

[step]: https://en.wikipedia.org/wiki/ISO_10303-21
[stl]: https://en.wikipedia.org/wiki/STL_(file_format)
