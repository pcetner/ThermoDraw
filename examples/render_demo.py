"""Three demo scenes for the README.

    python examples/render_demo.py

Writes light and dark SVGs to docs/assets/. Colours are baked rather than
left as custom properties, because GitHub serves README images through an
<img> tag and picks the variant with <picture> media queries.

Everything here is laid out by hand at explicit coordinates. That is the
current state of the library: it places one symbol at a time. The network
layer that would do this from a node/branch declaration is not built yet.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from thermodraw import (Diagram, core as S, layout, render, save,  # noqa: E402
                        symbols as sym, theme)

OUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "assets"


# ------------------------------------------------------------------ plumbing
def wire(*pts):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<polyline class="w" points="{d}"/>'


def node(x, y, r=5.5):
    return f'<circle class="node-open" cx="{x}" cy="{y}" r="{r}"/>'


def block(cx, cy, a, inner, dashed=False):
    return f'<g transform="{S.xf(cx, cy, a)}">{inner}{sym.rect(dashed)}</g>'


def ground(x, y, a=90, half=24, depth=13):
    """A hatched boundary band. a=90 lays it flat with the hatch below."""
    return f'<g transform="{S.xf(x, y, a)}">{S.hatched_wall(0, half, depth)}</g>'


# The four box interiors, taken from the library rather than rebuilt here.
HATCH, FLOW, WAVE, SEAM = (sym.tex_cond(), sym.tex_conv(),
                           sym.tex_rad(), sym.tex_contact())


# ------------------------------------------------------ scene 1 — the ladder
HERO = pathlib.Path(__file__).resolve().parent / "hero.json"


def hero():
    """A power device from junction to still air.

    Series conduction, a contact resistance at the mounting face, then
    convection and radiation in parallel to ambient, with two capacitances on
    the reference rail — which is what makes it a transient model rather than
    a steady-state one.

    Read from hero.json rather than built here. It used to be sixty lines of
    hand-placed coordinates; the model, the layout and the label solver do
    that work now, and the file is the same data an LLM would be given.
    """
    diagram = Diagram.from_json(HERO.read_text(encoding="utf-8"))
    return render(layout(diagram))


# --------------------------------------------------- scene 2 — the rosette
ROSETTE_TEX = [HATCH, FLOW, WAVE, SEAM]


def rosette(n=12, R=176):
    """One node losing heat by twelve parallel paths, each to a boundary.

    Every box is the same geometry placed through a different transform, and
    the mechanism texture rotates with it. Nothing here is drawn twice.
    """
    wall = R + S.BW / 2 + 16
    half = wall + 30
    b = []
    for i in range(n):
        a = 360 * i / n
        r = math.radians(a)
        cx, cy = half + R * math.cos(r), half + R * math.sin(r)
        inner = ROSETTE_TEX[i % 4]
        b += [wire((half + 7 * math.cos(r), half + 7 * math.sin(r)),
                   (half + (R - S.BW / 2) * math.cos(r),
                    half + (R - S.BW / 2) * math.sin(r))),
              wire((half + (R + S.BW / 2) * math.cos(r),
                    half + (R + S.BW / 2) * math.sin(r)),
                   (half + wall * math.cos(r), half + wall * math.sin(r))),
              block(cx, cy, a, inner, dashed=(i % 4 == 2)),
              ground(half + wall * math.cos(r), half + wall * math.sin(r),
                     a, half=21, depth=11)]
    b.append(node(half, half, 7))
    return sym.canvas(2 * half, 2 * half, "".join(b))


# ------------------------------------------------ scene 3 — the vocabulary
# Geometry that is not symmetric about its own origin, nudged so the cell
# reads as centred. The symbols themselves are correct; only this sheet
# cares where the ink sits inside a box.
#
# The rule is minus the ink bounding box centre, rounded. Measure it with
# `tests/test_frame.py::drawn_ink` rather than by eye — this sheet is a
# golden, so a wrong nudge gets blessed by `--update-goldens` in silence.
# ("fixed" is the one hand-set entry left, 10 right of its own ink centre.)
NUDGE = {"fixed": (28, -9), "break": (16, -16), "flux": (-3, 0)}


def vocabulary(cols=4, cw=250, ch=152):
    """Every symbol once, at rest, named and nothing more."""
    rows = (len(sym.SYMBOLS) + cols - 1) // cols
    b = []
    for i, s in enumerate(sym.SYMBOLS):
        dx, dy = NUDGE.get(s.key, (0, 0))
        cx = (i % cols) * cw + cw / 2
        cy = (i // cols) * ch + ch / 2 - 12
        b.append(f'<g transform="{S.xf(cx + dx, cy + dy, 0)}">{s.draw(0)}</g>')
        b.append(f'<text class="user" x="{cx}" y="{(i // cols) * ch + ch - 16}" '
                 f'text-anchor="middle">{s.name}</text>')
        if i % cols:
            b.append(f'<line class="tick" x1="{(i % cols) * cw}" '
                     f'y1="{(i // cols) * ch + 18}" x2="{(i % cols) * cw}" '
                     f'y2="{(i // cols) * ch + ch - 32}"/>')
    return sym.canvas(cw * cols, ch * rows, "".join(b))


SCENES = {"hero": hero, "rosette": rosette, "vocabulary": vocabulary}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in SCENES.items():
        svg = fn()
        for mode in ("light", "dark"):
            save(theme.bake(svg, mode), OUT / f"{name}-{mode}.svg")
    print(f"wrote {2 * len(SCENES)} files to {OUT}")


if __name__ == "__main__":
    main()
