"""Theme handling and export.

Published pages want CSS custom properties so one file follows the reader's
light/dark setting. Word, PowerPoint and most rasterisers ignore custom
properties entirely, so those targets need the colours resolved first. `bake`
does that resolution, and embeds the text faces for the same reason: a target
that cannot fetch a stylesheet cannot fetch a font either, and text rendered
in a substitute face does not match the widths the label solver cleared it
against.
"""
import base64
import functools
import pathlib
import re

FONT_DIR = pathlib.Path(__file__).parent / "fonts"

# IBM Plex is OFL-1.1 with Reserved Font Name "Plex", and a subset is a
# Modified Version under clause 3, so the vendored faces carry a different
# name. The stack still asks for the real font first: anyone who has it
# installed gets it, and the metrics are identical either way.
EMBEDDED = "ThermoDraw Sans"
STACK = f'"IBM Plex Sans","{EMBEDDED}","Helvetica Neue",Arial,sans-serif'

FACE_FILES = [("regular", "thermodraw-sans-400.woff2", "normal", 400),
              ("italic", "thermodraw-sans-italic.woff2", "italic", 400),
              ("semibold", "thermodraw-sans-600.woff2", "normal", 600)]

PALETTES = {
    "light": {
        "sym": "#1b1b1f", "panel": "#ffffff", "ink": "#16181d",
        "ink-2": "#6b7078", "ink-3": "#8b909b", "tex": "#9aa0ab",
        "rule": "#e2e4e9", "accent": "#b4442c",
        "sans": STACK,
    },
    "dark": {
        "sym": "#d8d6d1", "panel": "#171a1f", "ink": "#e9e7e2",
        "ink-2": "#a2a7b2", "ink-3": "#727884", "tex": "#767c88",
        "rule": "#2a2e36", "accent": "#e8996b",
        "sans": STACK,
    },
}

_VARS = """
  :root{--sym:#1b1b1f;--panel:#fff;--ink:#16181d;--ink-2:#6b7078;
        --ink-3:#8b909b;--tex:#9aa0ab;--rule:#e2e4e9;--accent:#b4442c;
        --sans:""" + STACK + """}
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]){--sym:#d8d6d1;--panel:#171a1f;
      --ink:#e9e7e2;--ink-2:#a2a7b2;--ink-3:#727884;--tex:#767c88;
      --rule:#2a2e36;--accent:#e8996b}}
  :root[data-theme="dark"]{--sym:#d8d6d1;--panel:#171a1f;--ink:#e9e7e2;
    --ink-2:#a2a7b2;--ink-3:#727884;--tex:#767c88;--rule:#2a2e36;
    --accent:#e8996b}
"""

_VAR_RE = re.compile(r"var\(--([a-z0-9-]+)\)")


@functools.lru_cache(maxsize=None)
def font_face(face):
    """One @font-face rule with the subset inlined as a data URI."""
    name, style, weight = next(
        (n, s, w) for f, n, s, w in FACE_FILES if f == face)
    data = base64.b64encode((FONT_DIR / name).read_bytes()).decode("ascii")
    return (f'@font-face{{font-family:"{EMBEDDED}";font-style:{style};'
            f'font-weight:{weight};'
            f'src:url(data:font/woff2;base64,{data}) format("woff2")}}')


def faces_used(svg):
    """Which faces this diagram actually needs.

    Embedding all three costs about 79KB. A diagram with no text needs none,
    and most need two, so it is worth asking. The classes come from
    `symbols.CSS`: .user and .reg-lbl are semibold, .lbl is italic, the rest
    are regular.
    """
    if "<text" not in svg:
        return []
    used = ["regular"]
    if 'class="lbl"' in svg:
        used.append("italic")
    if 'class="user"' in svg or 'class="reg-lbl"' in svg:
        used.append("semibold")
    return used


def with_variables(svg):
    """Inject the custom-property block. Use for web embedding."""
    return svg.replace("<style>", "<style>" + _VARS, 1)


def bake(svg, theme="light", embed_font=True):
    """Resolve every var() to a literal. Use for Word, slides, rasterisers."""
    pal = PALETTES[theme]
    svg = _VAR_RE.sub(lambda m: pal.get(m.group(1), "#000"), svg)
    if embed_font:
        css = "".join(font_face(f) for f in faces_used(svg))
        svg = svg.replace("<style>", "<style>" + css, 1)
    return svg
