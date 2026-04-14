# bdbox

Parametric configuration and tooling for [build123d][build123d] models.

[![License](https://img.shields.io/github/license/smkent/bdbox)](https://github.com/smkent/bdbox/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/bdbox)](https://pypi.org/project/bdbox/)
[![Python](https://img.shields.io/pypi/pyversions/bdbox)](https://pypi.org/project/bdbox/)
[![CI](https://github.com/smkent/bdbox/actions/workflows/ci.yaml/badge.svg)](https://github.com/smkent/bdbox/actions/workflows/ci.yaml)
[![Coverage](https://codecov.io/gh/smkent/bdbox/branch/main/graph/badge.svg)](https://codecov.io/gh/smkent/bdbox)
[![Renovate](https://img.shields.io/badge/renovate-enabled-brightgreen?logo=renovatebot)](https://renovatebot.com)
[![GitHub stars](https://img.shields.io/github/stars/smkent/bdbox?style=social)](https://github.com/smkent/bdbox)

## Installation

```sh
pip install bdbox
```

## Features

Easily add **configurable parameters** to [build123d][build123d] models! Declare
typed parameters with defaults, then override them individually or with named
presets.

Great for simple models:

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

This provides a CLI with parameter value arguments, preset selection, and usage
information:

```sh
python mybox.py                 # Run with default values
python mybox.py --width 50      # Override a field value
python mybox.py --preset large  # Apply a named preset of values
python mybox.py --help          # Usage info with all parameters
```

**[See full details in the documentation!][docs]**

## Project template

This project is generated and maintained with [copier-python][copier-python].

[build123d]: https://build123d.readthedocs.io
[copier-python]: https://smkent.github.io/copier-python
[docs]: https://smkent.github.io/bdbox/parameters/
