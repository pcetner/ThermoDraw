"""The two README images.

    python examples/render_demo.py

Writes light and dark SVGs to docs/assets/. Colours are baked rather than
left as custom properties, because GitHub serves README images through an
<img> tag and picks the variant with <picture> media queries.

The hero is read from a file that holds no coordinates: the ladder solver
places it. The vocabulary sheet is laid out here, symbol by symbol, because
it is a table of glyphs and not a network.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from thermodraw import (Diagram, core as S, layout, render, save,  # noqa: E402
                        symbols as sym, theme)

OUT = pathlib.Path(__file__).resolve().parents[1] / "docs" / "assets"


# --------------------------------------------------- scene 1 — the hero
RAPTOR = pathlib.Path(__file__).resolve().parent / "raptor.json"


def raptor():
    """One square centimetre of a regeneratively cooled methalox throat wall.

    Combustion gas to methane coolant: gas-side convection and radiation in
    parallel, conduction through the copper-alloy liner, convection into the
    coolant channel, and the heat carried away to the injector.

    The file carries no `at`. Every number in it is an estimate from public
    figures for this class of engine; `examples/raptor.md` has the sources
    and the arithmetic, and `check --physics` is silent on it.
    """
    diagram = Diagram.from_json(RAPTOR.read_text(encoding="utf-8"))
    return render(layout(diagram))


# ------------------------------------------------ scene 2 — the vocabulary
# Geometry that is not symmetric about its own origin, nudged so the cell
# reads as centred. The symbols themselves are correct; only this sheet
# cares where the ink sits inside a box.
#
# The rule is minus the ink bounding box centre, rounded. Measure it with
# `tests/test_frame.py::drawn_ink` rather than by eye — this sheet is a
# golden, so a wrong nudge gets blessed by `--update-goldens` in silence.
# ("fixed" is the one hand-set entry left, 10 right of its own ink centre.)
NUDGE = {"fixed": (28, -9), "break": (16, -16), "flux": (-3, 0),
         "phase": (0, -7)}


def vocabulary(cols=4, cw=250, ch=152):
    """Every symbol once, at rest, named and nothing more.

    Laid out group by group, each group starting a new row. At twenty
    entries the order *is* the specification, and a plain left-to-right fill
    stops carrying it — a reader learning the vocabulary needs to see that
    the four box textures are one family and the sources are another.
    """
    by_key = {s.key: s for s in sym.SYMBOLS}
    cells, row = [], 0
    for _, keys in sym.GROUPS:
        for i, key in enumerate(keys):
            cells.append((by_key[key], row + i // cols, i % cols))
        row += (len(keys) + cols - 1) // cols

    b = []
    for s, r, c in cells:
        dx, dy = NUDGE.get(s.key, (0, 0))
        cx, top = c * cw + cw / 2, r * ch
        b.append(f'<g transform="{S.xf(cx + dx, top + ch / 2 - 12 + dy, 0)}">'
                 f'{s.draw(0)}</g>')
        b.append(f'<text class="user" x="{cx}" y="{top + ch - 16}" '
                 f'text-anchor="middle">{s.name}</text>')
        if c:
            b.append(f'<line class="tick" x1="{c * cw}" y1="{top + 18}" '
                     f'x2="{c * cw}" y2="{top + ch - 32}"/>')
    return sym.canvas(cw * cols, ch * row, "".join(b))


SCENES = {"raptor": raptor, "vocabulary": vocabulary}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in SCENES.items():
        svg = fn()
        for mode in ("light", "dark"):
            save(theme.bake(svg, mode), OUT / f"{name}-{mode}.svg")
    print(f"wrote {2 * len(SCENES)} files to {OUT}")


if __name__ == "__main__":
    main()
