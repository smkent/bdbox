---
title: Actions
icon: lucide/play
---

# Actions

!!! Abstract "bdbox **actions** perform operations on collected model geometry!"

    * **`export`** writes geometry to a STEP or STL file
    * **`run`** (the default) supports running models without any postprocessing
    * Run actions directly with model files, or using the **`bdbox`** runner

## Available actions

### run

`run` executes the model without any postprocessing. It is the default when no
action subcommand is given, so existing invocations like `python model.py`
continue to work unchanged. Any geometry display or export must be performed by
the model itself.

### export

`export` collects all geometry produced by the model and writes it to a file.
The output format is determined by the file extension (not case sensitive):

| Extension | Format |
|---|---|
| `.step` | [STEP][step] (Standard for the Exchange of Product model data) |
| `.stl` | [STL][stl] (stereolithography) |

## Invocation modes

Actions are available in two ways:

### Embedded

Any model that declares a [``Params``][bdbox.parameters.parameters.Params] or
[``Model``][bdbox.model.Model] subclass automatically receives action CLI
support. Run the model file directly with Python and supply the desired action
as a subcommand:

```sh
python model.py                     # Run (default)
python model.py run                 # Explicit run
python model.py export output.step  # Export to STEP
python model.py export output.stl   # Export to STL
```

### bdbox runner

The `bdbox` command can run any bdbox model file. It is useful for exporting
models without modifying them, and for scripting or automation:

```sh
bdbox model.py                      # Run (default)
bdbox model.py run                  # Explicit run
bdbox model.py export output.step   # Export to STEP
bdbox model.py export output.stl    # Export to STL
```

## Combining actions with parameter flags

Action subcommands and [parameter flags](../parameters/cli.md) may be used
together. Parameter flags may appear before or after the subcommand:

```sh
python model.py --width 50 export output.step
```

```sh
python model.py export output.step --width 50
```

The `bdbox` runner provides the same flexibility:

```sh
bdbox model.py --width 50 export output.step
```

[step]: https://en.wikipedia.org/wiki/ISO_10303-21
[stl]: https://en.wikipedia.org/wiki/STL_(file_format)
