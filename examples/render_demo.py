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
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from thermodraw import core as S, save, symbols as sym, theme  # noqa: E402

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


def cap(cx, cy, a):
    return f'<g transform="{S.xf(cx, cy, a)}">{sym.g_cap(a)}</g>'


# The four box interiors, taken from the library rather than rebuilt here.
HATCH, FLOW, WAVE, SEAM = (sym.tex_cond(), sym.tex_conv(),
                           sym.tex_rad(), sym.tex_contact())


# ------------------------------------------------------ scene 1 — the ladder
def hero():
    """A power device from junction to still air.

    Series conduction path, a contact resistance at the mounting face, then
    convection and radiation in parallel to ambient. Two capacitances drop to
    the reference rail, which is what makes it a transient model rather than
    a steady-state one.
    """
    Y, YT, YB, YR, YC = 150, 70, 238, 372, 278
    XJ, XC, XS = 200, 424, 648
    XSPLIT, XJOIN = 696, 936
    B1, B2, B3, XP = 312, 536, 816, 96
    hb = S.BW / 2
    b = []

    # heat in
    b += [f'<g transform="{S.xf(XP, Y, 0)}">'
          f'<line class="w" x1="-32" y1="0" x2="20" y2="0"/>{S.arrowhead(32)}</g>',
          wire((XP + 32, Y), (XJ, Y))]

    # series path
    b += [wire((XJ, Y), (B1 - hb, Y)), block(B1, Y, 0, HATCH),
          wire((B1 + hb, Y), (B2 - hb, Y)), block(B2, Y, 0, SEAM),
          wire((B2 + hb, Y), (XSPLIT, Y))]

    # convection and radiation in parallel
    b += [wire((XSPLIT, YT), (XSPLIT, YB)),
          wire((XSPLIT, YT), (B3 - hb, YT)), block(B3, YT, 0, FLOW),
          wire((B3 + hb, YT), (XJOIN, YT)),
          wire((XSPLIT, YB), (B3 - hb, YB)), block(B3, YB, 0, WAVE, dashed=True),
          wire((B3 + hb, YB), (XJOIN, YB)),
          wire((XJOIN, YT), (XJOIN, YR))]

    # reference rail, with the two capacitances hanging off it
    b.append(wire((XJ, YR), (XJOIN, YR)))
    for x in (XJ, XS):
        b += [wire((x, Y), (x, YR)), cap(x, YC, 90)]

    b += [node(XJ, Y), node(XC, Y), node(XS, Y), node(XJOIN, YR),
          wire((XJOIN, YR), (XJOIN, YR + 12)), ground(XJOIN, YR + 12)]

    lab = S.annotate
    lab(XP, Y, 0, b, user="Switching loss", name=S.sym_text("P", "d"),
        value="45 W", half=7, half_len=32)
    lab(XJ, Y, 0, b, user="Junction", name=S.sym_text("T", "j"),
        value="112 °C", half=5.5, half_len=5.5)
    lab(XC, Y, 0, b, user="Case", name=S.sym_text("T", "c"),
        value="78 °C", half=5.5, half_len=5.5)
    lab(XS, Y, 0, b, user="Sink base", name=S.sym_text("T", "s"),
        value="61 °C", half=5.5, half_len=5.5)
    lab(B1, Y, 0, b, user="Die attach", name=S.sym_text("R", "cond"),
        value="0.35 K/W", half=S.BH / 2, half_len=hb)
    lab(B2, Y, 0, b, user="Grease", name=S.sym_text("R", "contact"),
        value="0.15 K/W", half=S.BH / 2, half_len=hb)
    lab(B3, YT, 0, b, user="Fins → air", name=S.sym_text("R", "conv"),
        value="1.80 K/W", half=S.BH / 2, half_len=hb)
    lab(B3, YB, 0, b, user="Case → walls", name=S.sym_text("R", "rad"),
        value="6.40 K/W", half=S.BH / 2, half_len=hb)
    lab(XJ, YC, 90, b, user="Die", name=S.sym_text("C", "j"),
        value="0.9 J/K", half=15, half_len=15)
    lab(XS, YC, 90, b, user="Sink", name=S.sym_text("C", "s"),
        value="86 J/K", half=15, half_len=15)
    lab(XJOIN, YR, 90, b, user="Still air", name=S.sym_text("T", "amb"),
        value="40 °C", half=24, half_len=20)

    return sym.canvas(1060, 470, "".join(b))


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
NUDGE = {"fixed": (28, -9), "break": (20, 0), "flux": (-3, 0)}


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

_VIEWBOX = re.compile(r'viewBox="0 0 ([\d.]+) ([\d.]+)"')


def sized(svg):
    """Give the root explicit pixel dimensions.

    `canvas` emits width="100%", which is right for a page that owns its own
    column. A file loaded through an <img> tag has no column to fill, so it
    needs a real size to scale from.
    """
    w, h = _VIEWBOX.search(svg).groups()
    return svg.replace('width="100%"', f'width="{w}" height="{h}"', 1)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in SCENES.items():
        svg = sized(fn())
        for mode in ("light", "dark"):
            save(theme.bake(svg, mode), OUT / f"{name}-{mode}.svg")
    print(f"wrote {2 * len(SCENES)} files to {OUT}")


if __name__ == "__main__":
    main()
