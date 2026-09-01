"""The two thumbnails that would settle the notation bet.

    python docs/notation-test/make.py

`boxes.svg` is the hero as the library draws it. `zigzags.svg` is the same
network with the four resistance boxes replaced by circuit-notation zigzags —
and nothing else changed: same coordinates, same label solver, same text at
the same positions, same font. The only difference between the two files is
the glyph, which is the only thing the bet is about.

Show both to one thermal engineer who has never seen this library, at the
size they would be on a slide, and ask which path is convection. See README.md.
"""
import dataclasses
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from thermodraw import Diagram, layout, render, save, symbols, theme  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
BOXED = {"cond", "conv", "rad", "contact"}


def zigzag(a):
    """A resistor in circuit notation, the length of a box: leads, six peaks."""
    hb, peak = symbols.S.BW / 2, 8
    path = f"M{-hb},0 l7,{-peak}" + " l14,16 l14,-16" * 2 + f" l14,16 l7,{-peak}"
    return symbols.leads(hb) + f'<path class="w" d="{path}"/>'


def main():
    d = Diagram.from_json((ROOT / "examples" / "hero.json").read_text("utf-8"))
    boxes = layout(d)
    zigs = []
    for p in boxes:
        if p.symbol is not None and p.symbol.key in BOXED:
            # Same half/half_len, so the labels land in exactly the same
            # place: the glyph is the one variable.
            p = dataclasses.replace(p, symbol=dataclasses.replace(
                p.symbol, draw=zigzag, texture=None))
        zigs.append(p)
    for name, placements in (("boxes", boxes), ("zigzags", zigs)):
        svg = theme.bake(render(placements, size=d.size), "light")
        # A white ground of its own, so the file looks the same in every
        # viewer: the test is about a glance, and a dark host would decide it.
        svg = svg.replace("</style>", '</style><rect width="100%" height="100%" '
                          'fill="#ffffff"/>', 1)
        save(svg, HERE / f"{name}.svg")
    print("wrote boxes.svg and zigzags.svg")


if __name__ == "__main__":
    main()
