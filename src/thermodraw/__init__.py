"""ThermoDraw — thermal network diagrams for Python.

    from thermodraw import save, symbols, theme

    svg = symbols.diagonal_demo()
    save(theme.bake(svg, "light"), "out.svg")

Design notes and the reasoning behind each symbol live in CLAUDE.md.
"""
from . import core, io, symbols, theme
from .io import save

__version__ = "0.1.0"
__all__ = ["core", "io", "save", "symbols", "theme"]
