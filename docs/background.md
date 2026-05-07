---
title: Background
icon: lucide/lightbulb
---

# Background

As a 3D printing hobbyist, I have a growing collection of personal 3D models. As
with personal software projects, I enjoy publishing my models for others to use.
I discovered [build123d][build123d] after modeling with [OpenSCAD][openscad].

## From OpenSCAD to build123d

build123d has some [great advantages][build123d-vs-openscad] over OpenSCAD:

* Better geometry ([STEP][step] file export) than OpenSCAD's
  [mesh of vertexes][openscad-csg]
* Common CAD operations like [**`chamfer`**][build123d-chamfer] and
  [**`fillet`**][build123d-fillet] are simple
* [build123d models are Python programs][build123d-pypi], whereas
  [OpenSCAD uses its own modeling language][openscad-language]

Comparatively, build123d's development experience was lacking. OpenSCAD shines
in several other areas:

* Models are previewed automatically on save or hotkey
* Exporting model renders is simple (two key presses)
* OpenSCAD
  [even provides a GUI for setting toplevel variables][openscad-customizer]!
* Sharing models is as simple as publishing `*.scad` files. Sharing a build123d
  model which is an arbitrary Python program has a bit more friction. Users need
  to install build123d (perhaps in a virtualenv), [OCP CAD Viewer][ocp_vscode]
  using VSCode or standalone with its own instructions, and potentially edit
  variables in the model source for customization, etc. This is especially
  cumbersome for folks who aren't familiar with the Python ecosystem.

## Competing responsibilities

Additionally, I didn't like how build123d models needed to both **define the
model geometry** and **decide what to do with it** (e.g. viewing with
**`ocp_vscode.show()`** or exporting with **`build123d.export_step`**).

Models are code, which should be tracked in source control. Why should tracked
model geometry code need to be cluttered with miscellaneous actions? The code
should describe **what the model is**, not what is done with it afterward.

## Finding my footing

I first created some one-off tools to ease model preview/reload/export, but they
were disorganized, fragile, and I frequently had to relearn how to use them when
I worked on a model. I realized the overall development experience was
dissuading me from modeling with build123d, but the geometry advantages of
build123d are compelling enough that I didn't want to develop new models in
OpenSCAD. I also figured anyone with a similar workflow would need to build
their own duct-taped workflow tools.

## Enter bdbox

I built **`bdbox`** to be that missing tool. A model is just geometry and
optional parameters. **`bdbox`** lets you _use_ a model: preview, live reload,
parameters panel, CLI, and render export with simple commands.

**[Visit the documentation site to get started with `bdbox`!][docs]**

[docs]: https://smkent.github.io/bdbox/
[build123d-chamfer]: https://build123d.readthedocs.io/en/stable/direct_api_reference.html#topology.Mixin3D.chamfer
[build123d-fillet]: https://build123d.readthedocs.io/en/stable/direct_api_reference.html#topology.Mixin3D.fillet
[build123d-pypi]: https://pypi.org/project/build123d/
[build123d-vs-openscad]: https://build123d.readthedocs.io/en/stable/OpenSCAD.html
[build123d]: https://build123d.readthedocs.io
[ocp_vscode]: https://github.com/bernhard-42/vscode-ocp-cad-viewer
[openscad-csg]: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/CSG_Modelling
[openscad-customizer]: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Customizer
[openscad-language]: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual#The_OpenSCAD_Language_Reference
[openscad]: https://openscad.org/
[step]: https://en.wikipedia.org/wiki/ISO_10303-21
