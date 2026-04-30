# bdbox

A live development environment for [build123d][build123d] models.

[![License](https://img.shields.io/github/license/smkent/bdbox)](https://github.com/smkent/bdbox/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/bdbox)](https://pypi.org/project/bdbox/)
[![Python](https://img.shields.io/pypi/pyversions/bdbox)](https://pypi.org/project/bdbox/)
[![CI](https://github.com/smkent/bdbox/actions/workflows/ci.yaml/badge.svg)](https://github.com/smkent/bdbox/actions/workflows/ci.yaml)
[![Coverage](https://codecov.io/gh/smkent/bdbox/branch/main/graph/badge.svg)](https://codecov.io/gh/smkent/bdbox)
[![Renovate](https://img.shields.io/badge/renovate-enabled-brightgreen?logo=renovatebot)](https://renovatebot.com)
[![GitHub stars](https://img.shields.io/github/stars/smkent/bdbox?style=social)](https://github.com/smkent/bdbox)

[See the documentation site for full project details!][docs]

## Installation

```sh
pip install bdbox
```

## Works with any build123d model

Use `bdbox` with build123d models:

```python
# mybox.py
from build123d import Box

result = Box(10, 10, 10)
```

Export to STEP or STL with `bdbox`:

```sh
bdbox mybox.py export out.step  # Export to STEP
```

```sh
bdbox mybox.py export out.stl   # Export to STL
```

Python module paths work too:

```sh
bdbox mypackage.models.mybox export out.step
```

```sh
python -m mypackage.models.mybox export out.step
```

View your model in your browser with [OCP CAD Viewer][ocp_vscode], started
automatically. `bdbox` automatically re-renders your model on save:

```sh
bdbox mybox.py view
```

```sh
bdbox mypackage.models.mybox view
```

**[See more about actions in the documentation!][docs-actions]**

## Add parameters for interactive customization

Easily create parametric models using `bdbox`! Declare typed parameters with
defaults, then override them individually or with named presets:

```python
from bdbox import Float, Int, Params, Preset, show
from build123d import Box

class P(Params):
    width = Float(10.0, min=5, max=100)
    length = Float(20.0, min=5, max=100)
    thickness = Int(2, min=1, max=10)
    presets = (
        Preset("small", width=5.0, length=8.0),
        Preset("large", width=80.0, length=40.0, thickness=5),
    )

result = Box(P.width, P.length, P.thickness)
show(result)
```

Or inherit from the provided base class for reusable, importable models:

```python
from bdbox import Float, Int, Model, Preset
from build123d import Box

class MyBox(Model):
    width = Float(10.0, min=5, max=100)
    length = Float(20.0, min=5, max=100)
    thickness = Int(2, min=1, max=10)
    presets = (
        Preset("small", width=5.0, length=8.0),
        Preset("large", width=80.0, length=40.0, thickness=5),
    )

    def build(self):
        return Box(self.width, self.length, self.thickness)
```

Parameters become CLI flags automatically:

```sh
python mybox.py                 # Run with default values
python mybox.py view            # View with live reload
python mybox.py --width 50      # Override a field value
python mybox.py --preset large  # Apply a named preset
python mybox.py --help          # Usage info with all parameters
```

Export geometry to STEP or STL files using the built-in `export` action:

```sh
python mybox.py export output.step  # Export to STEP
python mybox.py export output.stl   # Export to STL
```

**[See more about parameters in the documentation!][docs-parameters]**

## Project template

This project is generated and maintained with [copier-python][copier-python].

[build123d]: https://build123d.readthedocs.io
[copier-python]: https://smkent.github.io/copier-python
[docs]: https://smkent.github.io/bdbox/
[docs-actions]: https://smkent.github.io/bdbox/actions/
[docs-parameters]: https://smkent.github.io/bdbox/parameters/
[ocp_vscode]: https://github.com/bernhard-42/vscode-ocp-cad-viewer
