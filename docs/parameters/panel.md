---
title: Parameters Panel
icon: lucide/sliders-horizontal
---

# Parameters Panel

The [`view` action][view] web UI includes a parameters panel. When your model
defines [parameters](index.md) and/or [presets](presets.md), controls for those
parameters and presets appear in the parameters panel.

The availabe parameters and presets in the parameters panel update as edits to
your model adds, changes, or removes parameters.

![bdbox UI](../bdbox-ui.png){ align=left }

??? Example "Source code"

    ```python
    --8<-- "bdbox/examples/demo.py"
    ```

## Starting the web UI

The web UI starts automatically with the `view` action:

=== "`bdbox` with **file**"

    ```sh
    bdbox model.py view
    ```

=== "`bdbox` with **module**"

    ```sh
    bdbox mypackage.mymodule view
    ```

=== "Direct with **file**"

    ```sh
    python model.py view
    ```

=== "Direct with **module**"

    ```sh
    python -m mypackage.mymodule view
    ```

With the `view` command running, the UI is available at:

[**http://localhost:4040**](http://localhost:4040){ .md-button .md-button--primary target="_blank" }

## Parameter controls

!!! Info Reminder

    A model declares [parameters](index.md) as class attributes just like
    with [dataclasses][dataclasses], using standard type annotations and/or the
    provided [field factory functions](fields.md).

Parameter controls are generated automatically from your model's parameter
definitions.

Changing any parameter value triggers an automatic model re-render with the
updated value applied.

## Presets

If your model defines [presets][presets], preset buttons appear above the
parameter form. Clicking a preset button applies the preset's values and
re-renders the model automatically.

Click **Reset** to restore all parameters to their default values.

## Console

The console pane captures the model's standard error output, such as build
errors and tracebacks.

[presets]: presets.md
[view]: ../actions/view.md
