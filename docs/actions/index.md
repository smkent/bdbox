---
title: Overview
icon: lucide/play
---

# Actions

!!! Abstract "bdbox provides **actions** for your [build123d][build123d] models!"

    * Easily view or export models with `bdbox`!

    * Regular build123d models must both build and determine how to use
      model geometry.

    * With `bdbox`, a model only needs to build its geometry, leaving `bdbox` to
      perform actions on that geometry.

    * Optionally specify model geometry, or let `bdbox` locate model geometry
      from a model's global variables automatically.

## Available actions

| Action | Description |
|---|---|
| [`export`](export.md) | Export model geometry to a STEP or STL file |
| [`view`](view.md) | View model geometry with [OCP CAD Viewer][ocp_vscode] |
| `run` (default) | No geometry processing. Model is responsible for using its own geometry. |

## Invocation modes

Actions work the same way whether models are run with `bdbox` or directly:

=== "With `bdbox`"

    The `bdbox` command works with any build123d model, including models without
    any `bdbox` imports:

    ```sh
    bdbox model.py                      # Run (default)
    bdbox model.py view                 # View in OCP CAD Viewer
    bdbox model.py export output.step   # Export to STEP
    ```

=== "Direct"

    The CLI is automatically provided on any model with a
    [``Params``][bdbox.parameters.parameters.Params] or
    [``Model``][bdbox.model.Model] subclass. Run the model file itself to use
    the CLI:

    ```sh
    python model.py                     # Run (default)
    python model.py view                # View in OCP CAD Viewer
    python model.py export output.step  # Export to STEP
    ```

[build123d]: https://build123d.readthedocs.io
[ocp_vscode]: https://github.com/bernhard-42/vscode-ocp-cad-viewer
