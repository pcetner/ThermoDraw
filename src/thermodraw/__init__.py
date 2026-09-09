"""ThermoDraw — thermal network diagrams for Python.

A diagram is data. You write it, or an LLM writes it, and three pure stages
turn it into a document:

    dict / JSON  ->  Diagram  ->  placements  ->  SVG
                      model      layout        render
                             (solve fills in the `at` you left out)

    from thermodraw import Diagram, layout, render, save, theme

    d = Diagram.from_json(open("diagram.json").read())
    save(theme.with_variables(render(layout(d))), "out.svg")

`render` emits CSS custom properties with no fallback, so its output goes
through `theme` before it is saved: `with_variables` for the web, `bake` for
Word, slides and rasterisers. Without one of them the file draws nothing.

`DiagramBuilder` is sugar over the same data, and `symbols` still places one
symbol at a time for anything the model does not yet cover.

The schema is docs/schema.md. Design notes and the reasoning behind each
symbol are in CLAUDE.md.
"""
from . import core, io, model, symbols, theme
from ._check import Finding, Report, check
from ._describe import Description, describe
from ._layout import Placement, layout
from ._page import page
from ._render import render
from ._solve import solve
from ._analysis import PhysicsResult, solve_physics
from ._session import assess_physics
from .builder import DiagramBuilder
from .io import save
from .model import Branch, Diagram, DiagramError, Node, Rail, Source
from .model import Region, ControlVolume, ControlSurface, Transfer, Annotation
from .symbols import SYMBOLS, Symbol

__version__ = "1.0.0"
__all__ = [
    # the data
    "Diagram", "Node", "Branch", "Source", "Rail", "DiagramError",
    "Region", "ControlVolume", "ControlSurface", "Transfer", "Annotation",
    # the pipeline
    "solve", "layout", "render", "Placement", "DiagramBuilder",
    # is it any good?
    "check", "Report", "Finding", "solve_physics", "PhysicsResult", "assess_physics",
    # is it the one you meant?
    "describe", "Description",
    # the same drawing, as a page you can interact with
    "page",
    # the vocabulary
    "Symbol", "SYMBOLS",
    # output
    "save", "theme",
    # still public, for placing one symbol at a time
    "symbols", "core", "model", "io",
]
