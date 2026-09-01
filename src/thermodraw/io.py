"""Writing diagrams to disk.

SVG is UTF-8 by definition. Python's `open` is not: on Windows it defaults to
the system code page, which cannot encode the arrow in "Sink → Ambient" or the
double prime in q″ — three of the twelve symbols. The failure is quiet in the
worst way, because `diagonal_demo` happens to contain no non-ASCII at all, so
the documented example passes and real use crashes.
"""
import pathlib

DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'


def save(text, path, declaration=True):
    """Write text as UTF-8, with LF endings, and return the path.

    The XML declaration is redundant when a file is served as image/svg+xml,
    where UTF-8 is already the default. It is not redundant when the file is
    opened from disk by Word, PowerPoint or a rasteriser, which is exactly the
    audience `theme.bake` exists for.

    It is added only to something that is actually an SVG. This function is
    the one place in the library that writes a file, so it also gets used for
    JSON and for anything else a caller has in hand, and prepending markup to
    those quietly corrupts them.
    """
    path = pathlib.Path(path)
    if declaration and _is_svg(text):
        text = DECLARATION + text
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def _is_svg(text):
    head = text.lstrip()[:200].lower()
    return head.startswith("<svg") or (
        head.startswith("<?xml") and "<svg" in head)
