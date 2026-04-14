---
title: Fields
icon: lucide/text-cursor-input
---

# Fields

!!! info "Automatic [dataclasses][dataclasses]"

    Subclasses of **[``Params``][bdbox.parameters.parameters.Params]** and
    **[``Model``][bdbox.model.Model]** are automatically created as
    [dataclasses][dataclasses] with no `@dataclass` decorator!

Parameters are declared as class attributes just like with dataclasses.

## Attribute annotations

For typed parameters with no constraints, simply declare annotated class
attributes with or without default values:

=== "Params class"

    ```python
    from bdbox import Params

    class P(Params):
        count: int
        width: float
        length: float = 20.0
        extra: int = 5
        toggle: bool = False
        label: str = "untitled"
    ```

=== "Model class"

    ```python
    from bdbox import Model

    class MyModel(Model):
        count: int
        width: float
        length: float = 20.0
        extra: int = 5
        toggle: bool = False
        label: str = "untitled"

        def build(self):
            pass
    ```

### Inference from default values

Unlike [dataclasses][dataclasses], parameters with no constraints and a default
value may also be declared without type annotations. With this pattern, the type
is inferred from the default value:

=== "Params class"

    ```python
    from bdbox import Params

    class P(Params):
        count = 5
        width = 10.0
        toggle = False
        label = "untitled"
    ```

=== "Model class"

    ```python
    from bdbox import Model

    class MyModel(Model):
        count = 5
        width = 10.0
        toggle = False
        label = "untitled"

        def build(self):
            pass
    ```

!!! Note "Static type checking"

    Adding type annotations even when optional may improve static type checking.

## Factory functions

Fields can be created with constraints using these factory functions.

| Factory | Value type | Required | Optional |
|---|---|---|---|
| [``Int``][bdbox.parameters.field_factories.Int] | `int` | `default` | `min`, `max`, `step`, `description` |
| [``Float``][bdbox.parameters.field_factories.Float] | `float` | `default` | `min`, `max`, `step`, `description` |
| [``Bool``][bdbox.parameters.field_factories.Bool] | `bool` | `default` | `description` |
| [``Str``][bdbox.parameters.field_factories.Str] | `str` | `default` | `min_length`, `max_length`, `description` |
| [``Choice``][bdbox.parameters.field_factories.Choice] | `T` | `default`, `choices` | `description` |

!!! Note "Static type checking"

    Type annotations are not required for attributes created using these factory
    functions. However, adding annotations may improve static type checking:

    === "Params class"

        ```python
        from bdbox import Int, Params

        class P(Params):
            count = Int(3)      # works without type annotation
            size: int = Int(5)  # with optional type annotation
        ```

    === "Model class"

        ```python
        from bdbox import Int, Model

        class MyModel(Model):
            count = Int(3)      # works without type annotation
            size: int = Int(5)  # with optional type annotation

            def build(self):
                pass
        ```

### Field descriptions

These factory functions accept an optional `description` keyword argument for a
human-readable description. In the CLI, a field's description replaces its name
in the model's `--help` output:

```python
width = Float(10.0, min=5, max=100, description="Box width in mm")
```

```text
--width 5 <= FLOAT <= 100
             Box width in mm (default: 10.0)
```

Without a description, the field name is used as the label:

```text
--width 5 <= FLOAT <= 100
             width (default: 10.0)
```

### Function details

#### Int and Float

Numeric fields which accept `min`, `max`, and `step` constraints:

=== "Params class"

    ```python
    from bdbox import Float, Int, Params

    class P(Params):
        width = Float(10.0, min=5.0, max=200.0, step=0.5)
        count = Int(3, min=1, max=20)
    ```

=== "Model class"

    ```python
    from bdbox import Float, Int, Model

    class MyModel(Model):
        width = Float(10.0, min=5.0, max=200.0, step=0.5)
        count = Int(3, min=1, max=20)

        def build(self):
            pass
    ```

`step` is a hint for any external controls. If provided on field creation, it
must be a positive number. It is not used for runtime validation.

#### Bool

Boolean field (`True` or `False`)

=== "Params class"

    ```python
    from bdbox import Bool, Params

    class P(Params):
        hollow = Bool(False)
    ```

=== "Model class"

    ```python
    from bdbox import Bool, Model

    class MyModel(Model):
        hollow = Bool(False)

        def build(self):
            pass
    ```

#### Str

String field for text.

`min_length` and `max_length` are inclusive bounds, validated at declaration
time. If provided, the `default` value's length must fall within that range.

=== "Params class"

    ```python
    from bdbox import Params, Str

    class P(Params):
        label = Str("thing", min_length=3, max_length=20)
    ```

=== "Model class"

    ```python
    from bdbox import Model, Str

    class MyModel(Model):
        label = Str("thing", min_length=3, max_length=20)

        def build(self):
            pass
    ```

#### Choice

[``Choice``][bdbox.parameters.field_factories.Choice] lets you offer a fixed
menu of values. This is useful for options such as material types, quality
levels, or any other discrete selection. The default must be one of the listed
choices:

=== "Params class"

    ```python
    from bdbox import Choice, Params

    class P(Params):
        material = Choice("wood", ["wood", "metal", "plastic"])
        side_count = Choice(6, [3, 4, 6, 8, 12])
        scale = Choice(1.0, [0.5, 1.0, 2.0])
    ```

=== "Model class"

    ```python
    from bdbox import Choice, Model

    class MyModel(Model):
        material = Choice("wood", ["wood", "metal", "plastic"])
        side_count = Choice(6, [3, 4, 6, 8, 12])
        scale = Choice(1.0, [0.5, 1.0, 2.0])

        def build(self):
            pass
    ```

## Dataclass fields

For complex types or custom defaults, use
[``dataclasses.field``][dataclasses.field] just like with dataclasses:

=== "Params class"

    ```python
    from bdbox import Params
    from dataclasses import field

    class P(Params):
        tags: set[str] = field(default_factory=set)
        vector: list[int] = field(default_factory=list)
    ```

=== "Model class"

    ```python
    from bdbox import Model
    from dataclasses import field

    class MyModel(Model):
        tags: set[str] = field(default_factory=set)
        vector: list[int] = field(default_factory=list)

        def build(self):
            pass
    ```

!!! Tip

    [Types supported by tyro][tyro-supported] work with the
    [command line interface](cli.md).


[tyro]: https://brentyi.github.io/tyro/
[tyro-supported]: https://brentyi.github.io/tyro/whats_supported/
