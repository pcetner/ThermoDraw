"""ThermoDraw — thermal network diagrams for Python.

    from thermodraw import symbols, theme

    svg = symbols.diagonal_demo()
    open("out.svg", "w").write(theme.bake(svg, "light"))

Design notes and the reasoning behind each symbol live in CLAUDE.md.
"""
from . import core, symbols, theme

__version__ = "0.1.0"
__all__ = ["core", "symbols", "theme"]
