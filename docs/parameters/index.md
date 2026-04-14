---
title: Getting Started
icon: lucide/package-open
---

# Parameters

!!! Abstract "bdbox provides **typed, named parameters** support for your [build123d][build123d] models!"

    * Declare parameters as class attributes like standard
      [Python dataclasses][dataclasses]
    * Specify optional parameter constraints with
      [simple field helpers](fields.md)
    * Automatically created [Command line interface](cli.md) with usage
      information for running models with different parameter values
    * When all parameters have default values,
      **running `python model.py` just works!**

Choose from one of two declaration styles by subclassing either
**[``Params``][bdbox.parameters.parameters.Params]** or
**[``Model``][bdbox.model.Model]**:

=== "Params class"

    ```python
    from bdbox import Float, Int, Params, Preset, show
    from build123d import Box

    class P(Params):
        width = Float(10.0, min=5, max=100)
        length = Float(10.0, min=5, max=100)
        thickness = Int(3, min=1, max=10)

        presets = (Preset("large", width=50.0, thickness=8),)

    show(Box(P.width, P.length, P.thickness))
    ```

=== "Model class"

    ```python
    from bdbox import Float, Int, Model, Preset
    from build123d import Box

    class MyBox(Model):
        width = Float(10.0, min=5, max=100)
        length = Float(10.0, min=5, max=100)
        thickness = Int(3, min=1, max=10)

        presets = (Preset("large", width=50.0, thickness=8),)

        def build(self):
            return Box(self.width, self.length, self.thickness)
    ```

!!! Info "Automatic [dataclasses][dataclasses]"

    Subclasses of **[``Params``][bdbox.parameters.parameters.Params]** and
    **[``Model``][bdbox.model.Model]** automatically function as
    [dataclasses][dataclasses] with no `@dataclass` decorator!

    Declare parameters as class attributes just like with dataclasses.

* **Params** subclasses provide parameter values as direct class attributes (for
  example, `P.width`). With **Params**, construct your model after the class
  declaration to access parameter values. Geometry is collected either by
  [``show``][bdbox.geometry.show], or by scanning the script's global variables
  as a fallback. Only one `Params` subclass per script is permitted.

* **Model** subclasses provide parameter values as instance attributes within
  class methods (for example, `self.width`). With **Model**, implement
  the [``build``][bdbox.model.Model.build] method to construct your model
  geometry. Execute your model with the [``run``][bdbox.model.Model.run] method.
  If there is only one `Model` subclass, `run` will be called automatically if
  not invoked explicitly. Multiple `Model` subclasses in one script are
  supported, but `run` must then be called manually on each.

!!! tip "Which style to choose"

    * **Model** subclasses are recommended for reusable models. They can be
      imported and used in other code and subclassed for reuse.

    * **Params** is convenient for single model scripts or experimentation with
      minimal scaffolding.

    Both model styles are [dataclasses][dataclasses], support the same
    [fields](fields.md), and provide the same [command line interface](cli.md).

!!! warning "Use one style per script"

    Subclassing both [``Params``][bdbox.parameters.parameters.Params] and
    [``Model``][bdbox.model.Model] in the same script is not supported and
    produces an error.

[build123d]: https://build123d.readthedocs.io
