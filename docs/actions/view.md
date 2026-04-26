---
title: View
icon: lucide/eye
---

# View

The `view` action renders and displays your model in your browser using
[OCP CAD Viewer][ocp_vscode], started automatically. Models are watched for
changes, and re-run when files are saved.

## Usage

=== "With `bdbox`"

    ```sh
    bdbox model.py view
    ```

=== "Direct"

    ```sh
    python model.py view
    ```

### Options

Optional arguments to `view` include:

* `--no-open-browser`: Don't open a browser tab when starting the viewer
* `--no-watch`: Render model once, don't watch for changes
* `--export FILE`: Save rendered model to the specified file on each render

!!! Note

    For more information about file exports,
    [see the `export` command documentation](export.md).

See all options with `--help`:

=== "With `bdbox`"

    ```sh
    bdbox view --help
    ```

=== "Direct"

    ```sh
    python model.py view --help
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

=== "With `bdbox`"

    ```sh
    bdbox viewer --help
    ```

=== "Direct"

    ```sh
    python model.py viewer --help
    ```

[ocp_vscode]: https://github.com/bernhard-42/vscode-ocp-cad-viewer
