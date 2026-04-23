---
title: CLI
icon: lucide/terminal
---

# Command Line Interface (CLI)

[build123d][build123d] models with bdbox are Python programs. When run directly,
command line arguments are processed using [tyro][tyro]. Geometry is
collected automatically after a model finishes running. No entry point or
argument parsing code is needed.

## Invocation modes

| Command | Effect |
|---|---|
| `python model.py` | Build with all field defaults (equivalent to `run`) |
| `python model.py --width 25` | Override one or more fields |
| `python model.py --preset large` | Apply a named preset |
| `python model.py --preset large --width 25` | Preset as baseline, then override |
| `python model.py --help` | Show all fields, defaults, presets, and actions |
| `python model.py run` | Explicitly run the model |
| `python model.py view` | View geometry in OCP CAD Viewer |
| `python model.py export output.step` | Export geometry to a STEP file |
| `python model.py export output.stl` | Export geometry to an STL file |

See the [Actions](../actions/index.md) documentation for full details,
including the [view](../actions/view.md) and [export](../actions/export.md)
actions and use of the `bdbox` runner.

## Field flags

Each parameter becomes a `--field-name` flag. Underscores in field names are
converted to hyphens. For example, a value for:

```python
wall_thickness = Float(3.0)
```

can be overridden with the option `--wall-thickness`.

### Boolean fields

Boolean fields are represented as a pair of `--flag` / `--no-flag` options:

```text
--hollow, --no-hollow  (default: False)
```

```sh
python model.py --hollow        # Set to True
python model.py --no-hollow     # Set to False
```

## Help output

`--help` lists every field with its type, description, and default value, plus
available presets and actions:

```text
usage: MyBox [-h] [OPTIONS] [{run,view,export}]

╭─ options ──────────────────────────────────────────────╮
│ -h, --help             show this help message and exit │
│ --preset {None,small,large}                            │
│                        (default: None)                 │
│ --width 5 <= FLOAT <= 100                              │
│                        (default: 10.0)                 │
│ --thickness 1 <= FLOAT <= 10                           │
│                        (default: 3.0)                  │
╰────────────────────────────────────────────────────────╯
╭─ subcommands ──────────────────────────────────────────╮
│ (default: run)                                         │
│   • run      Run the model.                            │
│   • view     View model geometry.                      │
│   • export   Export geometry to a STEP or STL file.    │
╰────────────────────────────────────────────────────────╯
```

## Automatic execution

**Params:** Subclassing [``Params``][bdbox.parameters.parameters.Params]
provides the CLI and resolves parameter values.

**Model:** Defining exactly one [``Model``][bdbox.model.Model] subclass
in a model program enables the model to be built without calling
the [``run``][bdbox.model.Model.run] method. For more control over program
execution, `run` may be called manually. If multiple subclasses are defined, a
warning is printed and `run` must be manually called on the desired class.

=== "Params class"

    ```python
    from bdbox import Params, show
    from build123d import Box

    class P(Params):
        size = Float(10.0, min=5.0, max=20.0)

    # Parameter values are now accessible on P
    cube = Box(P.size, P.size, P.size)
    ```

=== "Model class"

    ```python
    from bdbox import Model
    from build123d import Box

    class MyBox(Model):
        size = Float(10.0, min=5.0, max=20.0)

        def build(self):
            # Parameter values are accessible on the current instance
            return Box(self.size, self.size, self.size)
    ```

## Geometry collection

**Params:** One or more calls to [``show``][bdbox.geometry.show] accumulate
geometry in call order. If `show` is never called (and
[``Params``][bdbox.parameters.parameters.Params] is subclassed within the
[invoked script][__main__]), bdbox scans the program's global variables for
[``build123d.Shape``][topology.Shape] instances on completion.

**Model:** Geometry must be returned from the
[``build``][bdbox.model.Model.build] method.

=== "Params class"

    ```python
    from bdbox import Params, show
    from build123d import Box

    class P(Params):
        size = Float(10.0, min=5.0, max=20.0)

    cube = Box(P.size, P.size, P.size)
    show(cube)  # optional
    ```

=== "Model class"

    ```python
    from bdbox import Model
    from build123d import Box

    class MyBox(Model):
        size = Float(10.0, min=5.0, max=20.0)

        def build(self):
            return Box(self.size, self.size, self.size)

    MyModel.run()  # optional, as only one Model subclass is defined
    ```

[build123d]: https://build123d.readthedocs.io
[tyro]: https://brentyi.github.io/tyro/
