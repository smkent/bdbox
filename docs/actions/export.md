---
title: Export
icon: lucide/download
---

# Export

The `export` action collects all geometry produced by the model and writes it
to a file. The output format is determined by the file extension (not case
sensitive):

| Extension | Format |
|---|---|
| `.step` | [STEP][step] (Standard for the Exchange of Product model data) |
| `.stl` | [STL][stl] (stereolithography) |

## Usage

=== "`bdbox` with **file**"

    ```sh
    bdbox model.py export output.step  # Export to STEP
    bdbox model.py export output.stl   # Export to STL
    ```

=== "`bdbox` with **module**"

    ```sh
    bdbox mypackage.mymodule export output.step  # Export to STEP
    bdbox mypackage.mymodule export output.stl   # Export to STL
    ```

=== "Direct with **file**"

    ```sh
    python model.py export output.step  # Export to STEP
    python model.py export output.stl   # Export to STL
    ```

=== "Direct with **module**"

    ```sh
    python -m mypackage.mymodule export output.step  # Export to STEP
    python -m mypackage.mymodule export output.stl   # Export to STL
    ```

## Combining with parameter flags

[Parameter flags](../parameters/cli.md) may appear before or after the
subcommand:

=== "`bdbox` with **file**"

    ```sh
    bdbox model.py --width 50 export output.step
    bdbox model.py export output.step --width 50
    ```

=== "`bdbox` with **module**"

    ```sh
    bdbox mypackage.mymodule --width 50 export output.step
    bdbox mypackage.mymodule export output.step --width 50
    ```

=== "Direct with **file**"

    ```sh
    python model.py --width 50 export output.step
    python model.py export output.step --width 50
    ```

=== "Direct with **module**"

    ```sh
    python -m mypackage.mymodule --width 50 export output.step
    python -m mypackage.mymodule export output.step --width 50
    ```

## Exporting renders for all presets

Models can be rendered for all [presets](../parameters/presets.md) and exported
to individual files using the `-a`/`--all-presets` option.

With this option, the output path becomes a directory (created automatically if
it doesn't exist). Each preset render is created in the output directory as
`{preset-name}.{format}`, e.g. `somepreset.step`. Model renders are exported as
STEP files by default, or can be exported as STL files using `--format stl`.

A model render with its default parameter values is also created as
`default.{format}`, e.g. `default.step`. For models with no presets, this is the only render created with
`-a`/`--all-presets`. This default render can be disabled with
`-n`/`--no-default`. Disabling the default render for models with no presets
will result in no outputs.

=== "`bdbox` with **file**"

    ```sh
    bdbox model.py export output/ --all-presets    # STEP (default)
    bdbox model.py export output/ -a --format stl  # STL
    ```

=== "`bdbox` with **module**"

    ```sh
    bdbox mypackage.mymodule export output/ --all-presets    # STEP (default)
    bdbox mypackage.mymodule export output/ -a --format stl  # STL
    ```

=== "Direct with **file**"

    ```sh
    python model.py export output/ --all-presets    # STEP (default)
    python model.py export output/ -a --format stl  # STL
    ```

=== "Direct with **module**"

    ```sh
    python -m mypackage.mymodule export output/ --all-presets    # STEP (default)
    python -m mypackage.mymodule export output/ -a --format stl  # STL
    ```

For a model with presets called `small` and `large`, the `output/` directory
would contain:

```
output/
├── default.step
├── large.step
└── small.step
```

[step]: https://en.wikipedia.org/wiki/ISO_10303-21
[stl]: https://en.wikipedia.org/wiki/STL_(file_format)
