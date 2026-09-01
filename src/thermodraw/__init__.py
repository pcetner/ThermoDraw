"""ThermoDraw — thermal network diagrams for Python.

A diagram is data. You write it, or an LLM writes it, and three pure stages
turn it into a document:

    dict / JSON  ->  Diagram  ->  placements  ->  SVG
                      model      layout        render

    from thermodraw import Diagram, layout, render, save

    d = Diagram.from_json(open("diagram.json").read())
    save(render(layout(d)), "out.svg")

`DiagramBuilder` is sugar over the same data, and `symbols` still places one
symbol at a time for anything the model does not yet cover.

The schema is docs/schema.md. Design notes and the reasoning behind each
symbol are in CLAUDE.md.
"""
from . import check as _check_mod, core, io, layout as _layout_mod
from . import describe as _describe_mod
from . import model, render as _render_mod
from . import symbols, theme
from .builder import DiagramBuilder
from .check import Finding, Report, check
from .describe import Description, describe
from .page import page
from .io import save
from .layout import Placement, layout
from .model import Branch, Diagram, DiagramError, Node, Rail, Source
from .render import render
from .symbols import SYMBOLS, Symbol

__version__ = "0.2.0"
__all__ = [
    # the data
    "Diagram", "Node", "Branch", "Source", "Rail", "DiagramError",
    # the pipeline
    "layout", "render", "Placement", "DiagramBuilder",
    # is it any good?
    "check", "Report", "Finding",
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
