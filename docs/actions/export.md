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

=== "With `bdbox`"

    ```sh
    bdbox model.py export output.step   # Export to STEP
    bdbox model.py export output.stl    # Export to STL
    ```

=== "Direct"

    ```sh
    python model.py export output.step  # Export to STEP
    python model.py export output.stl   # Export to STL
    ```

## Combining with parameter flags

[Parameter flags](../parameters/cli.md) may appear before or after the
subcommand:

=== "With `bdbox`"

    ```sh
    bdbox model.py --width 50 export output.step
    bdbox model.py export output.step --width 50
    ```

=== "Direct"

    ```sh
    python model.py --width 50 export output.step
    python model.py export output.step --width 50
    ```

[step]: https://en.wikipedia.org/wiki/ISO_10303-21
[stl]: https://en.wikipedia.org/wiki/STL_(file_format)
