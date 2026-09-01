"""Writing diagrams to disk.

SVG is UTF-8 by definition. Python's `open` is not: on Windows it defaults to
the system code page, which cannot encode the arrow in "Sink → Ambient" or the
double prime in q″ — three of the twelve symbols. The failure is quiet in the
worst way, because `diagonal_demo` happens to contain no non-ASCII at all, so
the documented example passes and real use crashes.
"""
import pathlib

DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'


def save(svg, path, declaration=True):
    """Write an SVG as UTF-8, with LF endings, and return the path.

    The declaration is redundant when the file is served as image/svg+xml,
    where UTF-8 is already the default. It is not redundant when the file is
    opened from disk by Word, PowerPoint or a rasteriser, which is exactly the
    audience `theme.bake` exists for.
    """
    path = pathlib.Path(path)
    if declaration and not svg.startswith("<?xml"):
        svg = DECLARATION + svg
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    return path
