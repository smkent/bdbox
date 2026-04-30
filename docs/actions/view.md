---
title: View
icon: lucide/eye
---

# View

The `view` action renders and displays your model in your browser using
[OCP CAD Viewer][ocp_vscode], started automatically. Models being viewed
automatically re-render when model files are saved.

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
* `--no-watch`: Render model once, don't watch for changes
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

## Viewer process management

The `view` action starts OCP CAD Viewer automatically. The viewer may also be
managed directly with the `viewer` subcommand:

```sh
bdbox viewer start           # Start OCP CAD Viewer
bdbox viewer start --restart # Restart even if already running
bdbox viewer stop            # Stop OCP CAD Viewer
bdbox viewer status          # Show viewer URL and PID
```

See all options with `--help`:

=== "`bdbox` with **file**"

    ```sh
    bdbox viewer --help  # Model not required for --help
    ```

=== "`bdbox` with **module**"

    ```sh
    bdbox viewer --help  # Model not required for --help
    ```

=== "Direct with **file**"

    ```sh
    python model.py viewer --help
    ```

=== "Direct with **module**"

    ```sh
    python -m mypackage.mymodule viewer --help
    ```

[ocp_vscode]: https://github.com/bernhard-42/vscode-ocp-cad-viewer
