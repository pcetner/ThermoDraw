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
import html
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from ._layout import layout as _layout, network, pieces as _pieces
from ._render import PADDING, compose

# A label's side is a unit vector, not one of the four `core.PAGE_SIDES`
# names — once `angle` is in play it points wherever the branch normal does.
# These are the eight a reader can name; anything else is reported as degrees.
COMPASS = [((0.0, -1.0), "above"), ((0.0, 1.0), "below"),
           ((-1.0, 0.0), "left"), ((1.0, 0.0), "right"),
           ((0.7071, -0.7071), "above right"), ((-0.7071, -0.7071), "above left"),
           ((0.7071, 0.7071), "below right"), ((-0.7071, 0.7071), "below left")]

# How close a direction must be to one of the eight to borrow its name.
NEAR = 0.96

# `core.sym_text` sets a subscript as a `<tspan>`. Read back as `R_cond`, so
# the description says what the reader will see rather than what the SVG says.
_TSPAN = re.compile(r"<tspan[^>]*>(.*?)</tspan>")


def label_text(label):
    """The two lines of one label, as the reader would read them.

    Without this a description cannot tell a 41 J/K mass hung on the right
    node from one hung on the wrong node: the geometry is identical and only
    the words differ. Which makes it the one thing worth printing, for a tool
    whose question is whether this is the diagram you meant.
    """
    if label is None:
        return ""
    stated = " = ".join(x for x in (label.name, label.value) if x)
    parts = [x for x in (label.user, stated) if x]
    # An extra is prose or a `(symbol, value)` pair; a pair reads the same
    # way the value line above it does.
    for x in getattr(label, "extra", ()):
        if x:
            parts.append(x if isinstance(x, str) else " = ".join(x))
    # The author's text, as written. Escaping happens in
    # `core.build_block`, downstream of the `Label` this reads, so
    # `label.user` has nothing to undo: a `<` an author typed is a `<`
    # here, as it is in the drawing.
    #
    # A subscript is the exception, and the claim above used to be made
    # of the whole string. `core.sym_text` escapes the subscript on the
    # way into its `<tspan>`, because that is where it enters markup, so
    # a `sub` of "a&b" was reported as `T_a&amp;b` on a row whose label
    # beside it read "Fins & fans". Undo it where it was done, and
    # nowhere else.
    return _TSPAN.sub(lambda m: "_" + html.unescape(m.group(1)),
                      " | ".join(parts))


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
    """One drawn thing: where it sits, and where its text went.

    Keyed on the placement rather than on the label, because `compose` skips
    a label with nothing to say — so an element carrying no text had no row
    at all. A `break` branch names no quantity by design; give one no `label`
    and it used to vanish from the description entirely, surviving only as a
    number in the counts.

    `at` is the element. `label_at` is its text, which is a different point
    and the whole reason `side` is worth printing.
    """

    ref: str
    kind: str
    at: Tuple[float, float]
    angle: float = 0.0
    side: str = ""
    size: Tuple[float, float] = (0.0, 0.0)
    label_at: Optional[Tuple[float, float]] = None
    says: str = ""
    pushed: float = 0.0
    flipped: bool = False
    clear: bool = True

    def text(self):
        where = f"({self.at[0]:.0f}, {self.at[1]:.0f})"
        # Only when it is turned. Printing "angle 0" on every row of a flat
        # ladder buries the one source that is not.
        if self.angle % 360:
            where += f" a{self.angle % 360:g}"
        if self.label_at is None:
            return f"  {self.ref:<22.22s} {self.kind:<15.15s} {where:<17s} "                    "(no label)"
        notes = []
        if self.flipped:
            notes.append("flipped")
        if self.pushed:
            notes.append(f"pushed {self.pushed:.0f}")
        if not self.clear:
            notes.append("OVERLAPS")
        notes.append(self.says)
        tail = "   ".join(n for n in notes if n)
        return (f"  {self.ref:<22.22s} {self.kind:<15.15s} {where:<17s}"
                f" {self.side:<12s} {self.size[0]:>4.0f}x"
                f"{self.size[1]:<4.0f} {tail}").rstrip()


@dataclass
class Description:
    """The drawing as prose, with the numbers kept as numbers."""

    source: str = "diagram"
    canvas: Tuple[float, float] = (0.0, 0.0)
    counts: Dict[str, int] = field(default_factory=dict)
    lines: List[Line] = field(default_factory=list)
    nodes: List[Tuple[str, str, Tuple[float, float]]] = field(
        default_factory=list)
    # A boundary node whose wall was turned, by id. Only the turned ones:
    # printing `wall down` on every fixed node would bury the one that is
    # not, the same reason `a0` is not printed on every row.
    walls: Dict[str, str] = field(default_factory=dict)
    # What `units.T` declared, if anything, and the unit it is on. Where a
    # wall landed was the one thing nothing could report; whether `K` meant
    # absolute or a rise was the other.
    scale: Optional[str] = None
    temperature_unit: str = ""
    # The rail is a wire like any other in the placements, so it vanished into
    # the count. `rail.reference` is documented as inert — it records which
    # node the rail *is* and does nothing — which makes this the only place it
    # could ever be checked against what was meant.
    rail: Optional[Tuple[str, float, Tuple[float, float]]] = None
    edges: List[Tuple[str, str, str]] = field(default_factory=list)
    pieces: List[List[str]] = field(default_factory=list)
    # Beside each edge, in the same order: (count, arrangement, directed).
    # The network block used to print `a --flow-branch-- b` with the same
    # symmetric dashes as a resistance, so a `flow` written backwards read
    # identically, and `j --cond-- ihs` gave no hint of eight paths; four
    # clean-room readers said the block could not confirm the one thing
    # each most needed confirmed.
    detail: List[Tuple[Optional[int], Optional[str], bool]] = field(
        default_factory=list)
    # (index, node, kind, outward) per source. The block that says what is
    # joined to what left out the elements that inject all the heat: three
    # readers noted a source on the wrong node would leave it byte-identical.
    sources: List[Tuple[int, str, str, bool]] = field(default_factory=list)

    def text(self):
        out = [f"{self.source}: canvas {self.canvas[0]:.0f} x "
               f"{self.canvas[1]:.0f}, "
               f"{sum(1 for l in self.lines if l.label_at)} label"
               + ("" if sum(1 for l in self.lines if l.label_at) == 1 else "s")]

        out += [""] + _wrap("placements: ",
                            [f"{k} x{v}"
                             for k, v in sorted(self.counts.items())] or ["none"])

        if self.rail:
            ref, y, (x0, x1) = self.rail
            out += ["", f"rail: y {y:.0f}, span ({x0:.0f}, {x1:.0f}), "
                        f"reference {ref!r}"]
        if self.edges or self.sources or len(self.pieces) > 1:
            out += ["", "network:"]
            joined: Dict[Tuple[str, str], List[str]] = {}
            directed: List[str] = []
            details = self.detail or [(None, None, False)] * len(self.edges)
            for (a, b, kind), (count, arrangement, arrow) in zip(
                    self.edges, details):
                text = kind if not count else f"{kind} x{count} {arrangement}"
                if arrow:
                    directed.append(f"  {a} --{text}-> {b}")
                else:
                    joined.setdefault((a, b), []).append(text)
            for (a, b), kinds in joined.items():
                out.append(f"  {a} --{'/'.join(kinds)}-- {b}")
            out += directed
            # Heat reads left to right: into its node for a source that
            # arrives, out of it for one that leaves.
            for i, node, kind, outward in self.sources:
                out.append(f"  {node} --{kind}-> source {i}" if outward
                           else f"  source {i} --{kind}-> {node}")
            loose = [g for g in self.pieces if not any(
                set(g) & {a, b} for a, b, _ in self.edges)]
            for group in loose:
                out.append(f"  {', '.join(group)} -- nothing")
            if len(self.pieces) > 1:
                out.append(f"  {len(self.pieces)} pieces, not one network")
        if self.scale:
            what = "absolute" if self.scale == "absolute" \
                else "rise above ambient"
            out += ["", f"temperatures: {what}, in {self.temperature_unit}"]
        if self.nodes:
            out += ["", "nodes:"]
            out += [f"  {i:<14.14s} {k:<8s} at ({x:.0f}, {y:.0f})"
                    + (f" wall {self.walls[i]}" if i in self.walls else "")
                    for i, k, (x, y) in self.nodes]
        if self.lines:
            out += ["", "elements:"]
            out += [l.text() for l in self.lines]
        return "\n".join(out)

    def to_dict(self):
        return {
            "source": self.source,
            "canvas": list(self.canvas),
            "counts": dict(self.counts),
            "nodes": [dict({"id": i, "kind": k, "at": list(a)},
                           **({"wall": self.walls[i]} if i in self.walls
                              else {}))
                      for i, k, a in self.nodes],
            "scale": self.scale,
            "edges": [{"from": a, "to": b, "kind": k, "count": count,
                       "arrangement": arrangement, "directed": arrow}
                      for (a, b, k), (count, arrangement, arrow) in zip(
                          self.edges, self.detail or
                          [(None, None, False)] * len(self.edges))],
            "sources": [{"index": i, "node": node, "kind": kind,
                         "outward": outward}
                        for i, node, kind, outward in self.sources],
            "pieces": [list(g) for g in self.pieces],
            "rail": None if not self.rail else {
                "reference": self.rail[0], "y": self.rail[1],
                "span": list(self.rail[2])},
            "elements": [{"ref": l.ref, "kind": l.kind, "at": list(l.at),
                          "angle": l.angle, "says": l.says,
                          "label": None if l.label_at is None else {
                              "at": list(l.label_at), "side": l.side,
                              "width": l.size[0], "height": l.size[1],
                              "pushed": l.pushed, "flipped": l.flipped,
                              "clear": l.clear}}
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


# `network` and `_pieces` are `_layout.network` and `_layout.pieces`. Three of
# five acceptance readers named the network as the biggest thing missing
# here — "the one question describe exists to answer is the one it doesn't" —
# and `check.network-in-pieces` asks the same question. They used to build it
# separately, each parsing `ref` strings, and a node called `a->b` broke both.
# One builder, read by both, is what makes "they cannot disagree" true.


def _kind(p):
    """What this placement is, in the vocabulary the author writes.

    A branch's mechanism is on its `Symbol`, so it is read from there rather
    than re-derived from the ref string. Everything else is its element.
    """
    if p.element == "symbol" and p.symbol is not None:
        return f"symbol/{p.symbol.key}"
    return p.element


def describe(diagram, size: Optional[Sequence[float]] = None,
             padding: float = PADDING,
             source: str = "diagram") -> "Description":
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

    # By placement, in diagram order, so an element with no label still gets
    # a row. Keyed on identity: two placements can share a ref, and a symbol
    # and its own lead wires all do.
    rects = {id(r.owner): r for r in scene.rects if r.owner is not None}
    lines = []
    for p in placements:
        # A repeated group's copies say nothing individually: the anchor
        # carries the one label that speaks for all of them, so it stands in
        # the table and they stay out of it.
        # `ground` is here because a boundary wall is the one thing on the
        # page whose position nothing could report. It was counted on the
        # `placements:` line and given no row, so a reader asking "did that
        # wall land between the mount and its strut?" had only a rendered
        # picture to ask — and one clean-room reader, forbidden to render,
        # shipped the arrangement it could verify instead of the one it
        # wanted. The wall carries no text of its own, so the row comes out
        # `(no label)`, which is the same shape a `break` branch with no
        # label already takes.
        if p.element not in ("symbol", "node", "anchor", "ground")                 or not p.shown:
            continue
        if p.element == "symbol" and p.copy is not None:
            continue
        rect = rects.get(id(p))
        kind = _kind(p)
        if p.element == "anchor":
            group = [q for q in placements
                     if q.ref == p.ref and q.symbol is not None]
            kind = (f"{_kind(group[0])} x{len(group)}" if group else "group")
        # A wall carries its node's `ref`, so a row for it would collide with
        # that node's own row and anything keyed on `ref` would lose one of
        # the two. It is the node's wall, and saying so is both unique and
        # what a reader would call it.
        ref = f"wall of {p.ref}" if p.element == "ground" else (p.ref or "?")
        line = Line(ref=ref, kind=kind, at=(p.at[0], p.at[1]),
                    angle=p.angle, says=label_text(p.label))
        if rect is not None:
            left, top, bw, bh = rect
            line.label_at = (left + bw / 2, top + bh / 2)
            line.side = side_word(rect.side)
            line.size = (bw, bh)
            line.pushed = round(rect.used - rect.solved, 1)
            line.flipped, line.clear = rect.flipped, rect.clear
        lines.append(line)

    edges = network(placements)
    # The same walk `network` makes, for what it leaves out: one placement
    # per branch carries the group and the kind, and the symbol key says
    # which kind is the directed one.
    detail: List[Tuple[Optional[int], Optional[str], bool]] = []
    seen: set = set()
    for p in placements:
        if p.role != "branch" or p.symbol is None or p.ref in seen:
            continue
        seen.add(p.ref)
        detail.append((p.count if p.count and p.count > 1 else None,
                       p.arrangement if p.count and p.count > 1 else None,
                       p.symbol.key == "flow-branch"))
    # `q.symbol is not None` is inside the generator, so mypy cannot carry
    # the narrowing out to the comprehension body; the local does.
    kept = [q for q in placements
            if q.role == "source" and q.symbol is not None]
    sources = [(i, p.ends[0], p.symbol.key, bool(p.outward))   # keys = kinds
               for i, p in enumerate(kept) if p.symbol is not None]
    return Description(
        source=source,
        canvas=(round(bx1 - bx0, 1), round(by1 - by0, 1)),
        counts=dict(Counter(_kind(p) for p in placements)),
        lines=lines,
        nodes=[(n.id, n.kind, tuple(n.at)) for n in diagram.nodes if n.at],
        walls={n.id: n.wall for n in diagram.nodes if n.wall != "down"},
        scale=diagram.scale,
        temperature_unit=diagram.units.get("T", ""),
        edges=edges,
        detail=detail,
        sources=sources,
        pieces=_pieces(edges,
                       [n.id for n in diagram.nodes]),
        rail=None if not diagram.rail else (
            diagram.rail.reference, diagram.rail.y,
            tuple(diagram.rail.span) if diagram.rail.span else
            (min(xs), max(xs)) if (xs := [n.at[0] for n in diagram.nodes
                                          if n.at]) else (0.0, 0.0)))
