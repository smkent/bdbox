---
title: Presets
icon: lucide/sliders-vertical
---

# Presets

A preset is a saved group of parameter values. Instead of overriding multiple
values every time you want a particular configuration, give those values a name
and apply them all at once with a preset. This is useful for creating defined
variations of models such as different sizes and feature sets.

## Declaring presets

Presets are declared alongside fields using
[``Preset``][bdbox.parameters.preset.Preset].

=== "Params class"

    Define a `presets` tuple of [``Preset``][bdbox.parameters.preset.Preset] as
    a [``Params``][bdbox.parameters.parameters.Params] subclass attribute:

    ```python
    class P(Params):
        width = Float(10.0, min=5, max=200)
        thickness = Float(3.0, min=1, max=20)

        presets = (
            Preset("small", width=15.0, thickness=2.0),
            Preset("large", width=100.0, thickness=10.0),
        )
    ```

=== "Model class"

    Define a `presets` tuple of [``Preset``][bdbox.parameters.preset.Preset] as
    a [``Model``][bdbox.model.Model] subclass attribute:

    ```python
    class MyBox(Model):
        width = Float(10.0, min=5, max=200)
        thickness = Float(3.0, min=1, max=20)

        presets = (
            Preset("small", width=15.0, thickness=2.0),
            Preset("large", width=100.0, thickness=10.0),
        )

        def build(self):
            pass
    ```

Presets don't need to cover every field. Any field not listed in a preset keeps
its default value.

## Using presets via the CLI

Select a preset with `--preset`:

=== "`bdbox` with **file**"

    ```sh
    bdbox model.py --preset large
    ```

=== "`bdbox` with **module**"

    ```sh
    bdbox mypackage.mymodule --preset large
    ```

=== "Direct with **file**"

    ```sh
    python model.py --preset large
    ```

=== "Direct with **module**"

    ```sh
    python -m mypackage.mymodule --preset large
    ```

### Combining presets with overrides

Specific field values take precedence over preset values. Use a preset as a
baseline and adjust individual fields as needed. For example, in the CLI:

=== "`bdbox` with **file**"

    ```sh
    bdbox model.py --preset large --thickness 5.0
    ```

=== "`bdbox` with **module**"

    ```sh
    bdbox mypackage.mymodule --preset large --thickness 5.0
    ```

=== "Direct with **file**"

    ```sh
    python model.py --preset large --thickness 5.0
    ```

=== "Direct with **module**"

    ```sh
    python -m mypackage.mymodule --preset large --thickness 5.0
    ```

Field value precedence, from highest to lowest:

1. Field override values
2. Preset values
3. Field default values

## Preset descriptions

Presets accept an optional `description` shown in `--help` output:

```python
Preset("large", description="Extra large version", width=100.0, thickness=10.0)
```

## Programmatic use

Presets can be applied when instantiating a
[``Model``][bdbox.model.Model] or
[``Params``][bdbox.parameters.parameters.Params] subclass in code.

* Apply a preset by name:
    ```python
    model = MyBox(preset="large")
    ```
* Apply a preset and override additional fields:
    ```python
    model = MyBox(preset="large", thickness=5.0)
    ```
* [``with_preset``][bdbox.parameters.parameters.Params.with_preset] is
  equivalent but may more easily pass static type checks:
    ```python
    model = MyBox.with_preset("large", thickness=5.0)
    ```
