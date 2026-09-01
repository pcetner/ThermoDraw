"""Build a diagram in Python rather than writing it as data.

    python examples/build_ladder.py

Same model underneath as examples/hero.json — the builder only constructs it.
Anything you can say here is expressible as a dict, which is what `to_json`
at the bottom demonstrates: this script prints the schema form of what it
just drew, and that JSON renders identically.

A LED module on a heatsink: die to board to sink to still air, with the sink
mass on the reference rail.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from thermodraw import DiagramBuilder, save, theme  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"   # not setuptools' build/


def ladder():
    """Heat runs left to right, hottest first, reference rail along the bottom."""
    d = DiagramBuilder(R="K/W", C="J/K", T="°C", P="W")

    # Nodes carry a place and a temperature. `sub` names the place; the
    # library never sets it for you.
    d.node("j", "LED junction", "96", at=(200, 140), sub="j")
    d.node("b", "Board", "71", at=(420, 140), sub="b")
    d.node("s", "Sink base", "58", at=(640, 140), sub="s")
    d.node("amb", "Still air", "35", at=(860, 330),
           kind="fixed", sub="amb", angle=90)

    # Branches carry a mechanism. The subscript on a resistance is structural
    # and set by the library, so the label is where you say which path it is.
    d.branch("j", "b", "cond", "Die attach", "0.9")
    d.branch("b", "s", "contact", "Pad", "0.4")
    # Route it along the top and down into ambient. Sending it along y=330
    # would lay it on top of the rail, which reads as shorting the sink to
    # the reference — the drawing has to say the topology, not just carry it.
    d.branch("s", "amb", "conv", "Fins → air", "2.6",
             via=[(860, 140)], at=(860, 235))

    # The rail is what the thermal mass returns to.
    d.rail("amb", y=330, span=(200, 860))
    d.branch("s", "rail", "cap", "Sink", "140", sub="s")

    # Heat appears at a node; it is not a two-terminal element.
    d.source("j", "diss", "Forward power", "12", sub="d", at=(96, 140))
    return d


def main():
    OUT.mkdir(exist_ok=True)
    d = ladder()

    save(d.svg(), OUT / "ladder.svg")                  # follows light/dark
    save(d.svg("light"), OUT / "ladder-light.svg")     # baked for Word
    print(f"wrote 2 files to {OUT}")

    schema = OUT / "ladder.json"
    save(d.to_json(), schema)
    print(f"the same diagram as data: {schema}")

    # and it round-trips: the data renders to the same bytes
    from thermodraw import DiagramBuilder as B
    assert B.from_dict(d.to_dict()).svg() == d.svg()
    print("data and builder agree")


if __name__ == "__main__":
    main()
