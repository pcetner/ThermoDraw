"""Theme handling and export.

Published pages want CSS custom properties so one file follows the reader's
light/dark setting. Word, PowerPoint and most rasterisers ignore custom
properties entirely, so those targets need the colours resolved first.
`bake` does that resolution.
"""
import re

PALETTES = {
    "light": {
        "sym": "#1b1b1f", "panel": "#ffffff", "ink": "#16181d",
        "ink-2": "#6b7078", "ink-3": "#8b909b", "tex": "#9aa0ab",
        "rule": "#e2e4e9", "accent": "#b4442c",
        "sans": '"IBM Plex Sans", "Helvetica Neue", Arial, sans-serif',
    },
    "dark": {
        "sym": "#d8d6d1", "panel": "#171a1f", "ink": "#e9e7e2",
        "ink-2": "#a2a7b2", "ink-3": "#727884", "tex": "#767c88",
        "rule": "#2a2e36", "accent": "#e8996b",
        "sans": '"IBM Plex Sans", "Helvetica Neue", Arial, sans-serif',
    },
}

_VARS = """
  :root{--sym:#1b1b1f;--panel:#fff;--ink:#16181d;--ink-2:#6b7078;
        --ink-3:#8b909b;--tex:#9aa0ab;--rule:#e2e4e9;--accent:#b4442c;
        --sans:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif}
  @media (prefers-color-scheme:dark){
    :root:not([data-theme="light"]){--sym:#d8d6d1;--panel:#171a1f;
      --ink:#e9e7e2;--ink-2:#a2a7b2;--ink-3:#727884;--tex:#767c88;
      --rule:#2a2e36;--accent:#e8996b}}
  :root[data-theme="dark"]{--sym:#d8d6d1;--panel:#171a1f;--ink:#e9e7e2;
    --ink-2:#a2a7b2;--ink-3:#727884;--tex:#767c88;--rule:#2a2e36;
    --accent:#e8996b}
"""

_VAR_RE = re.compile(r"var\(--([a-z0-9-]+)\)")


def with_variables(svg):
    """Inject the custom-property block. Use for web embedding."""
    return svg.replace("<style>", "<style>" + _VARS, 1)


def bake(svg, theme="light"):
    """Resolve every var() to a literal. Use for Word, slides, rasterisers."""
    pal = PALETTES[theme]
    return _VAR_RE.sub(lambda m: pal.get(m.group(1), "#000"), svg)
