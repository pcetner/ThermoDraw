"""What got drawn, in words.

`check` answers "is this any good?". It cannot answer "is this the drawing I
meant?", and that turned out to be the question. Two acceptance agents, given
only `docs/schema.md` and no other context, independently asked for the same
thing: a text description of what came out — how many of each element, how big
the canvas is, which way each label went — enough to confirm intent without
opening a browser.

    from thermodraw import Diagram, describe
    print(describe(Diagram.from_json(open("d.json").read())).text())

It reports; it does not judge. `check` judges. Keeping them apart is why
`check`'s summary line can stay one trustworthy sentence: a describe that
also graded would have to hedge it.

Nothing here re-derives the page, for the same reason `check` does not.
`render.compose` hands back the occupancy the labels were solved against and
`core.annotate`'s account of each placement, and this reads those.

ASCII only, like the report: this goes to a terminal, and a Windows console is
cp1252. Ids and labels come from the file and can carry anything, which is why
`__main__` also softens stdout.
"""
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .layout import layout as _layout
# By name, not `from . import render`: the package rebinds `thermodraw.render`
# to the render *function*, so importing the module by attribute yields that.
from .render import PADDING, compose

# A label's side is a unit vector, not one of the four `core.PAGE_SIDES`
# names — once `angle` is in play it points wherever the branch normal does.
# These are the eight a reader can name; anything else is reported as degrees.
COMPASS = [((0.0, -1.0), "above"), ((0.0, 1.0), "below"),
           ((-1.0, 0.0), "left"), ((1.0, 0.0), "right"),
           ((0.7071, -0.7071), "above right"), ((-0.7071, -0.7071), "above left"),
           ((0.7071, 0.7071), "below right"), ((-0.7071, 0.7071), "below left")]

# How close a direction must be to one of the eight to borrow its name.
NEAR = 0.96


def side_word(side):
    """A unit direction as a word, or as degrees when it is between them."""
    if side is None:
        return "?"
    best, name = max(((side[0] * v[0] + side[1] * v[1], word)
                      for v, word in COMPASS), key=lambda p: p[0])
    if best >= NEAR:
        return name
    return f"{math.degrees(math.atan2(side[1], side[0])):.0f} deg"


@dataclass
class Line:
    """One labelled thing, and where its text went."""

    ref: str
    kind: str
    at: Tuple[float, float]
    side: str
    size: Tuple[float, float]
    pushed: float = 0.0
    flipped: bool = False
    clear: bool = True

    def text(self):
        notes = []
        if self.flipped:
            notes.append("flipped")
        if self.pushed:
            notes.append(f"pushed {self.pushed:.0f}")
        if not self.clear:
            notes.append("OVERLAPS")
        tail = ("   " + ", ".join(notes)) if notes else ""
        return (f"  {self.ref:<22.22s} {self.kind:<15.15s} {self.side:<12s}"
                f" {self.size[0]:>4.0f}x{self.size[1]:<.0f}{tail}")


@dataclass
class Description:
    """The drawing as prose, with the numbers kept as numbers."""

    source: str = "diagram"
    canvas: Tuple[float, float] = (0.0, 0.0)
    counts: Dict[str, int] = field(default_factory=dict)
    lines: List[Line] = field(default_factory=list)
    nodes: List[Tuple[str, str, Tuple[float, float]]] = field(
        default_factory=list)

    def text(self):
        out = [f"{self.source}: canvas {self.canvas[0]:.0f} x "
               f"{self.canvas[1]:.0f}, "
               f"{len(self.lines)} label" + ("" if len(self.lines) == 1 else "s")]

        out += [""] + _wrap("placements: ",
                            [f"{k} x{v}"
                             for k, v in sorted(self.counts.items())] or ["none"])

        if self.nodes:
            out += ["", "nodes:"]
            out += [f"  {i:<14.14s} {k:<8s} at ({x:.0f}, {y:.0f})"
                    for i, k, (x, y) in self.nodes]
        if self.lines:
            out += ["", "labels:"]
            out += [l.text() for l in self.lines]
        return "\n".join(out)

    def to_dict(self):
        return {
            "source": self.source,
            "canvas": list(self.canvas),
            "counts": dict(self.counts),
            "nodes": [{"id": i, "kind": k, "at": list(a)}
                      for i, k, a in self.nodes],
            "labels": [{"ref": l.ref, "kind": l.kind, "at": list(l.at),
                        "side": l.side, "width": l.size[0],
                        "height": l.size[1], "pushed": l.pushed,
                        "flipped": l.flipped, "clear": l.clear}
                       for l in self.lines],
        }


def _wrap(head, items, width=78):
    """`head` then a comma-separated list, indented under itself."""
    lines, current = [], head
    for i, item in enumerate(items):
        piece = item + ("," if i < len(items) - 1 else "")
        if len(current) + len(piece) + 1 > width and current.strip() != head.strip():
            lines.append(current.rstrip())
            current = " " * len(head)
        current += piece + " "
    return lines + [current.rstrip()]


def _kind(p):
    """What this placement is, in the vocabulary the author writes.

    A branch's mechanism is on its `Symbol`, so it is read from there rather
    than re-derived from the ref string. Everything else is its element.
    """
    if p.element == "symbol" and p.symbol is not None:
        return f"symbol/{p.symbol.key}"
    return p.element


def describe(diagram, size=None, padding=PADDING, source="diagram"):
    """What `render` would draw, as a `Description`.

    Takes a `Diagram` or a `DiagramBuilder`. Not a list of `Placement`, which
    `check` does take: the node kinds are on the diagram and placements have
    dropped them, and a describe that could only sometimes say what a node is
    would be worse than one that says so every time.
    """
    diagram = diagram.build() if hasattr(diagram, "build") else diagram
    if size is None:
        size = diagram.size
    placements = _layout(diagram)
    scene = compose(placements, size=size, padding=padding)
    bx0, by0, bx1, by1 = scene.box

    lines = []
    for rect in scene.rects:
        left, top, bw, bh = rect
        owner = rect.owner
        lines.append(Line(
            ref=rect.ref or "?", kind=_kind(owner) if owner else "?",
            at=(left + bw / 2, top + bh / 2), side=side_word(rect.side),
            size=(bw, bh), pushed=round(rect.used - rect.solved, 1),
            flipped=rect.flipped, clear=rect.clear))

    return Description(
        source=source,
        canvas=(round(bx1 - bx0, 1), round(by1 - by0, 1)),
        counts=dict(Counter(_kind(p) for p in placements)),
        lines=lines,
        nodes=[(n.id, n.kind, tuple(n.at)) for n in diagram.nodes if n.at])
