"""The diagram as a page, not a picture.

`render` emits the static SVG that Word, a README and every rasteriser need,
and that stays the canonical output. But a standalone `.svg` file cannot be
interacted with, and a repeated group has two forms a reader may want to swap
between — which is not SVG's fault: inline SVG in a page is fully scriptable
by its host. What is static is the *file*, not the format.

So this hands you a page. The same SVG, inline, plus the controls, in one
self-contained document with nothing fetched from anywhere.

    thermodraw page diagram.json -o diagram.html

The toggle is cheap because of how `layout` draws a repeated group: the
condensed form keeps the outermost copies, so both forms occupy exactly the
same footprint. Swapping is two `display` attributes. Nothing re-fits, no
label re-solves, and the checker's verdict holds for what you are looking at.

The script lives here and never in the SVG. A library whose first line is
"emits SVG, no runtime dependencies" should not put a widget inside every
picture it draws, and half its documented targets could not run one anyway.
"""
import html

from ._layout import layout as _layout
from ._render import PADDING, render, variant_id
from .theme import _VARS, faces_used, font_face

CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--panel);color:var(--ink);font-family:var(--sans);
     font-size:15px;line-height:1.55}
main{max-width:1200px;margin:0 auto;padding:28px 22px 56px;
     display:flex;flex-direction:column;gap:20px}
h1{margin:0;font-size:20px;font-weight:600;letter-spacing:-.01em}
figure{margin:0;overflow-x:auto}
svg{display:block;max-width:100%;height:auto}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;
          padding-top:4px;border-top:1px solid var(--rule)}
.controls p{margin:0;color:var(--ink-2);font-size:13px}
button{font:inherit;font-size:13px;color:var(--ink);background:transparent;
       border:1px solid var(--rule);border-radius:4px;padding:5px 11px;
       cursor:pointer}
button:hover{border-color:var(--ink-2)}
button[aria-pressed="true"]{border-color:var(--accent);color:var(--accent)}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (prefers-reduced-motion:no-preference){button{transition:border-color .15s}}

/* The two forms of a repeated group. Only the group's own ink moves: the
   canvas is already sized for the larger form, so expanding one disturbs
   nothing else on the page. Each copy carries its own delay, set by `render`
   from how far it sits off the centre line, so the fan runs open from the
   middle outwards instead of appearing all at once. */
.td-form{transition:opacity .16s linear}
.td-copy{opacity:1;transition:opacity .32s cubic-bezier(.2,.75,.3,1) var(--d,0ms)}
.td-form.td-off{opacity:0;pointer-events:none}
.td-form.td-off .td-copy{opacity:0;transition-delay:0ms}
@media (prefers-reduced-motion:reduce){
  .td-form,.td-copy{transition:none}
}
"""

SCRIPT = """
// The hidden form ships with display="none" so a static renderer that never
// runs this draws one form and only one. Swap that for a class the moment
// there is a script to animate it: `display` cannot be transitioned.
const show = (g, on) => g && g.classList.toggle('td-off', !on);
for (const b of document.querySelectorAll('button[data-shows]')) {
  for (const id of [b.dataset.shows, b.dataset.hides]) {
    const g = document.getElementById(id);
    if (!g) continue;
    const off = g.getAttribute('display') === 'none';
    g.removeAttribute('display');
    g.classList.toggle('td-off', off);
  }
  b.addEventListener('click', () => {
    const on = b.getAttribute('aria-pressed') !== 'true';
    b.setAttribute('aria-pressed', String(on));
    b.textContent = on ? b.dataset.less : b.dataset.more;
    show(document.getElementById(b.dataset.shows), on);
    show(document.getElementById(b.dataset.hides), !on);
  });
}
"""


def groups(placements):
    """The repeated groups, and the two forms each one was drawn in.

    Read back off the placements rather than off the diagram, so the ids here
    are the ids `render` actually wrote — the same reason `check` reads the
    scene instead of rebuilding it.
    """
    found = {}
    for p in placements:
        if not p.ref:
            continue
        g = found.setdefault(p.ref, {"ref": p.ref, "n": 0, "shown": None,
                                     "forms": set()})
        if p.variant is not None:
            g["forms"].add(p.variant)
            if p.shown:
                g["shown"] = p.variant
        if p.symbol is not None and p.copy is not None:
            g["n"] = max(g["n"], p.copy + 1)
    # Both forms, or there is nothing to swap: a group of three draws every
    # copy and has no condensed form at all, so a control on it would hide a
    # symbol and put nothing in its place.
    return [{k: v for k, v in g.items() if k != "forms"}
            for g in found.values()
            if g["n"] > 1 and {"full", "condensed"} <= g["forms"]]


def _button(group):
    """One control. `data-shows` is the form the press reveals."""
    condensed = group["shown"] == "condensed"
    more = f"Show all {group['n']}"
    less = "Condense"
    return (
        f'<button type="button" aria-pressed="{str(not condensed).lower()}"'
        f' data-shows="{variant_id(group["ref"], "full")}"'
        f' data-hides="{variant_id(group["ref"], "condensed")}"'
        f' data-more="{html.escape(more)}" data-less="{html.escape(less)}">'
        f'{html.escape(less if not condensed else more)}</button>')


def page(diagram, size=None, padding=PADDING, title=None):
    """A self-contained HTML document with the diagram inline.

    Takes a `Diagram` or a `DiagramBuilder`, like `describe`.
    """
    diagram = diagram.build() if hasattr(diagram, "build") else diagram
    placements = _layout(diagram)
    size = size if size is not None else diagram.size
    svg = render(placements, size=size, padding=padding)
    heading = title or diagram.title or "Thermal network"

    repeated = groups(placements)
    controls = ""
    if repeated:
        controls = ('<div class="controls"><p>Repeated groups:</p>'
                    + "".join(_button(g) for g in repeated) + "</div>")

    faces = "".join(font_face(f) for f in faces_used(svg))
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(heading)}</title>"
        f"<style>{faces}{_VARS}{CSS}</style></head><body><main>"
        f"<h1>{html.escape(heading)}</h1>"
        f"<figure>{svg}</figure>"
        f"{controls}"
        "</main>"
        f"<script>{SCRIPT}</script>"
        "</body></html>\n")
