# bdbox

**[build123d][build123d]** development with live preview and
interactive parameters

[![License](https://img.shields.io/github/license/smkent/bdbox)](https://github.com/smkent/bdbox/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/bdbox)](https://pypi.org/project/bdbox/)
[![Python](https://img.shields.io/pypi/pyversions/bdbox)](https://pypi.org/project/bdbox/)
[![CI](https://github.com/smkent/bdbox/actions/workflows/ci.yaml/badge.svg)](https://github.com/smkent/bdbox/actions/workflows/ci.yaml)
[![Coverage](https://codecov.io/gh/smkent/bdbox/branch/main/graph/badge.svg)](https://codecov.io/gh/smkent/bdbox)
[![Renovate](https://img.shields.io/badge/renovate-enabled-brightgreen?logo=renovatebot)](https://renovatebot.com)
[![GitHub stars](https://img.shields.io/github/stars/smkent/bdbox?style=social)](https://github.com/smkent/bdbox)

![Screenshot][docs-screenshot-ui]

**[See the documentation site for full project details!][docs]**

## Why?

I discovered [build123d][build123d] after modeling with [OpenSCAD][openscad].
build123d has some [great advantages][build123d-vs-openscad] over OpenSCAD:

* Better geometry ([STEP][step] file export) than OpenSCAD's
  [mesh of vertexes][openscad-csg]
* Common CAD operations like [**`chamfer`**][build123d-chamfer] and
  [**`fillet`**][build123d-fillet] are simple
* [build123d models are Python programs][build123d-pypi], whereas
  [OpenSCAD uses its own modeling language][openscad-language]

Comparatively, build123d's development experience was lacking. OpenSCAD previews
a model on save or hotkey, makes exporting a model render simple, and
[even provides a GUI for setting toplevel variables][openscad-customizer]!
I started with some self-made tooling to work around these drawbacks, but having
to remember how to use and maintain it resulted in me working on models less.

I built **`bdbox`** to be the missing tool I wanted: Let models just define
their geometry plus optional parameters, and let **`bdbox`** handle everything
else!

**[See more background info in the documentation!][docs-background]**

## Installation

```sh
pip install bdbox
```

## Works with any build123d model

Use `bdbox` with any existing build123d script — no imports required:

```python
# mymodel.py
from build123d import Box

result = Box(10, 10, 10)
```

Export to STEP or STL:

```sh
bdbox mymodel.py export out.step  # Export to STEP
bdbox mymodel.py export out.stl   # Export to STL
```

View your model in the browser with [OCP CAD Viewer][ocp_vscode], started
automatically:

```sh
bdbox mymodel.py view
```

Module paths work too:

```sh
bdbox mypackage.mymodule view
bdbox mypackage.mymodule export out.step
```

**[See more about actions in the documentation!][docs-actions]**

## Interactive parameter panel

Add parameters to your model and run with `view` to open an interactive
parameter panel in your browser. Adjust sliders, enter values, and select
presets — the model re-renders automatically on every change.

<!-- Screenshot: parameter panel UI -->

**[See more about the parameter panel in the documentation!][docs-panel]**

## Add parameters

Declare typed parameters with defaults and constraints:

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

Or inherit from `Model` for reusable, importable models:

```python
from bdbox import Float, Int, Model, Preset
from build123d import Box

class MyModel(Model):
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
python mymodel.py                 # Run with default values
python mymodel.py view            # View with live reload and parameter panel
python mymodel.py --width 50      # Override a field value
python mymodel.py --preset large  # Apply a named preset
python mymodel.py --help          # Usage info with all parameters
```

Export geometry to STEP or STL files using the built-in `export` action:

```sh
python mymodel.py export output.step  # Export to STEP
python mymodel.py export output.stl   # Export to STL
```

**[See more about parameters in the documentation!][docs-parameters]**

## Project template

This project is generated and maintained with [copier-python][copier-python].

[build123d-chamfer]: https://build123d.readthedocs.io/en/stable/direct_api_reference.html#topology.Mixin3D.chamfer
[build123d-fillet]: https://build123d.readthedocs.io/en/stable/direct_api_reference.html#topology.Mixin3D.fillet
[build123d-pypi]: https://pypi.org/project/build123d/
[build123d-vs-openscad]: https://build123d.readthedocs.io/en/stable/OpenSCAD.html
[build123d]: https://build123d.readthedocs.io
[copier-python]: https://smkent.github.io/copier-python
[docs-actions]: https://smkent.github.io/bdbox/actions/
[docs-background]: https://smkent.github.io/bdbox/background/
[docs-panel]: https://smkent.github.io/bdbox/parameters/panel/
[docs-parameters]: https://smkent.github.io/bdbox/parameters/
[docs-screenshot-ui]: https://smkent.github.io/bdbox/bdbox-ui.png
[docs]: https://smkent.github.io/bdbox/
[ocp_vscode]: https://github.com/bernhard-42/vscode-ocp-cad-viewer
[openscad-csg]: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/CSG_Modelling
[openscad-customizer]: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Customizer
[openscad-language]: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual#The_OpenSCAD_Language_Reference
[openscad]: https://openscad.org/
[step]: https://en.wikipedia.org/wiki/ISO_10303-21
