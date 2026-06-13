---
title: View
icon: lucide/eye
---

# View

The `view` action provides a web UI for displaying rendered models in your
browser using [OCP CAD Viewer][ocp_vscode]. The UI server is started
automatically. Models being viewed automatically re-render when model files are
saved.

With the `view` command running, the UI is available at:

[**http://localhost:4040**](http://localhost:4040){ .md-button .md-button--primary target="_blank" }

## Usage

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

### Automatic re-render on save

With models from files (e.g. `model.py`), the viewer monitors the model file's
directory for changes.

With models from module (e.g. `mypackage.mymodule`), the viewer monitors all
imported files within the toplevel package namespace for changes. For example,
if a model in `mypackage.mymodule` imports `mypackage.othermodule`, then changes
within `mypackage.othermodule` will also cause the model to be re-rendered.
This is useful for models with shared components that aren't within the
model's own module, such as in monorepositories with shared parts or components.

### Options

Optional arguments to `view` include:

* `--no-open-browser`: Don't open a browser tab when starting the viewer
* `--export FILE`: Save rendered model to `FILE` on each render

!!! Note

    For more information about file exports,
    [see the `export` command documentation](export.md).

See all options with `--help`:

=== "`bdbox` with **file**"

    ```sh
    bdbox view --help  # Model not required for --help
    ```

=== "`bdbox` with **module**"

    ```sh
    bdbox view --help  # Model not required for --help
    ```

=== "Direct with **file**"

    ```sh
    python model.py view --help
    ```

=== "Direct with **module**"

    ```sh
    python -m mypackage.mymodule view --help
    ```

## Parameters panel

The web UI displays a parameters panel

When your model defines [parameters](../parameters/index.md), controls for those
parameters appear in the web UI's parameters panel. Adjust parameter values or
select presets in the panel. The model re-renders automatically.

See the [Parameter Panel](../parameters/panel.md) documentation for details.

[ocp_vscode]: https://github.com/bernhard-42/vscode-ocp-cad-viewer
