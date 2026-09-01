"""Turning placements into a document.

Pure and deterministic: the same placements always produce the same bytes.
This is where the plumbing the demo had to invent for itself lives — wires,
nodes, boundary grounds, and placing a symbol at a point and an angle.

Labels go on last so they sit above the geometry, and they are placed through
`core.annotate`, which still solves each block against its own symbol. It now
reports the rectangle it used, which is what lets the canvas size itself.
"""
import collections
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import core as S
from . import symbols as SY

PADDING = 24


class LabelRect(tuple):
    """(left, top, bw, bh) — still a 4-tuple, and now it knows whose it is.

    A tuple subclass rather than a NamedTuple, because a NamedTuple of six
    fields stops unpacking as four and every caller that writes
    `for left, top, bw, bh in rects` breaks. This unpacks as four, compares
    equal to the plain tuple it used to be, and carries the solver's account
    of the placement alongside — see `core.annotate`'s `report`.

    `core.annotate` keeps returning a plain tuple. The wrapping happens here,
    so the diagnostic type never reaches the solver.

    No `__slots__`: tuple is a variable-length built-in, and CPython refuses a
    nonempty `__slots__` on a subtype of one.
    """

    def __new__(cls, rect, owner=None, report=None):
        self = super().__new__(cls, rect)
        report = report or {}
        self.owner = owner
        self.ref = getattr(owner, "ref", None)
        self.side = report.get("side")
        self.solved = report.get("solved", 0.0)
        self.used = report.get("used", 0.0)
        self.flipped = report.get("flipped", False)
        self.clear = report.get("clear", True)
        return self

    def __repr__(self):
        return f"LabelRect({tuple(self)!r}, ref={self.ref!r})"


@dataclass
class Scene:
    """Everything one render knew, kept rather than thrown away.

    `draw` used to compute the occupancy, place every label against it, and
    drop it on the floor — so anything wanting to ask why a label sits where
    it does had to rebuild the page from the placements, and the first bug in
    that rebuild would be forgetting whatever the original forgot. This hands
    back the actual object the labels were solved against.

    `ink` is what the drawing covers with no padding; `box` is the canvas it
    was given. In the sized path the two are unrelated, which is the only way
    content can fall off the page.
    """

    parts: List[str] = field(default_factory=list)
    rects: List[LabelRect] = field(default_factory=list)
    occupancy: Optional[S.Occupancy] = None
    ink: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    box: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


def wire(points):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline class="w" points="{d}"/>'


def node(x, y, r=5.5):
    return f'<circle class="node-open" cx="{x:.1f}" cy="{y:.1f}" r="{r}"/>'


# What ground() draws, named so `bounds` can reserve exactly that and no
# more. These are not the only two wall numbers in the library — g_fixed_node
# draws (20, 12) and g_break (22, 13) — and they are deliberately not unified.
# The three are different walls at different scales, and two of them are
# specified by docs/symbol-reference.html, which is the declared visual record.
#
# Ints, not floats: they reach the markup through an f-string, so 24.0 would
# write `y="-24.0"` where the drawing has always said `y="-24"`, and the clip
# ids are content-addressed on exactly those numbers. Naming a constant is not
# supposed to move a single byte.
WALL_HALF, WALL_DEPTH = 24, 13

# The constant-temperature marking under a phase-change node: two rules of
# half-width PHASE_HALF at these depths. `symbols.g_phase_node` draws the same
# three numbers, and `tests/test_check.py` pins the two to each other — the
# lesson from `g_break`, which drew an arrangement the pipeline never had.
PHASE_HALF, PHASE_Y1, PHASE_Y2 = 13, 13, 19


def ground(x, y, angle=90, half=WALL_HALF, depth=WALL_DEPTH):
    """A hatched boundary band. angle=90 lays it flat, hatch below."""
    return (f'<g transform="{S.xf(x, y, angle)}">'
            f'{S.hatched_wall(0, half, depth)}</g>')


def place(sym, x, y, angle=0.0):
    """Boundary symbols mirror past vertical rather than arriving upside down."""
    mirror = sym.mirror and S.flips(angle)
    return f'<g transform="{S.xf(x, y, angle, mirror)}">{sym.draw(angle)}</g>'


def _segments(points):
    return [(points[i], points[i + 1]) for i in range(len(points) - 1)]


def _key(seg):
    """Segments match regardless of which way round they were routed."""
    a, b = ((round(p[0], 1), round(p[1], 1)) for p in seg)
    return (a, b) if a <= b else (b, a)


# The mark standing in for the copies a condensed group drops. Three dots,
# reading along the branch rather than stacked across it: an ellipsis means
# "and more of these" in the direction it runs, and stacking it perpendicular
# made it read as a decoration rather than as an omission.
ELLIPSIS_STEP = 9
ELLIPSIS_R = 2.4


def ellipsis(x, y, a, step=ELLIPSIS_STEP, r=ELLIPSIS_R):
    """Three dots where the copies a condensed group drops used to be."""
    return (f'<g transform="{S.xf(x, y, a)}">'
            + "".join(f'<circle class="fillsym" cx="{d * step}" cy="0" '
                      f'r="{r}"/>' for d in (-1, 0, 1))
            + '</g>')


# How far apart the copies of a group fade, in milliseconds. A whole group
# appearing at once reads as a dissolve; letting it run from the middle
# outwards reads as the fan opening, and moves no geometry at all — which is
# what keeps a toggle from disturbing anything else on the page.
STAGGER_MS = 26


def _variant_groups(variants):
    """One group per form, with each copy wrapped so it can fade in turn."""
    out = []
    for (ref, variant, shown), bucket in variants.items():
        copies = sorted(k for k in bucket if k is not None)
        mid = (copies[-1] / 2) if copies else 0.0
        body = []
        for key, markup in bucket.items():
            delay = 0 if key is None else round(abs(key - mid) * STAGGER_MS)
            body.append(f'<g class="td-copy" style="--d:{delay}ms">'
                        + "".join(markup) + "</g>")
        out.append(f'<g id="{variant_id(ref, variant)}" class="td-form"'
                   + ("" if shown else ' display="none"') + ">"
                   + "".join(body) + "</g>")
    return out


def variant_id(ref, variant):
    """A stable, content-addressed id for one form of a repeated group.

    Stable is the whole point: a page toggling between the two forms holds
    these in its markup, so they must not move when something unrelated in
    the diagram does. `core.uid` hashes what it is given and nothing else.
    """
    return S.uid("td", ref, variant)


def phase_mark(x, y):
    """Two short rules beneath a node whose temperature a phase change holds."""
    return "".join(
        f'<line class="w" x1="{x - PHASE_HALF:.1f}" y1="{y + dy}" '
        f'x2="{x + PHASE_HALF:.1f}" y2="{y + dy}"/>'
        for dy in (PHASE_Y1, PHASE_Y2))


def _phase_box(p):
    """The marking as an oriented box: (centre, half, angle)."""
    mid = (PHASE_Y1 + PHASE_Y2) / 2
    return ((p.at[0], p.at[1] + mid),
            (PHASE_HALF, (PHASE_Y2 - PHASE_Y1) / 2), 0.0)


def _wall(p):
    """(half, depth) for a ground placement, defaulting to what ground draws."""
    return tuple(p.wall) if p.wall else (WALL_HALF, WALL_DEPTH)


def _wall_box(p):
    """A ground as an oriented box: (centre, half, angle).

    The wall hangs off its anchor rather than straddling it — the line is at
    local x=0 and the hatch runs from there to `depth` — so its centre is half
    a depth along the local axis.
    """
    half, depth = _wall(p)
    r = math.radians(p.angle)
    centre = (p.at[0] + math.cos(r) * depth / 2,
              p.at[1] + math.sin(r) * depth / 2)
    return centre, (depth / 2, half), p.angle


def bounds(p):
    """What one placement covers on the page: (x0, y0, x1, y1).

    A node is `±radius` and stays that way. It is tempting to substitute the
    symbol's `half`/`half_len` — a fixed node carries 22 and 19 — but those
    are clearance numbers for the label solver, not ink: they would reserve 22
    units above a node that draws a 5.5 circle, and count the boundary wall a
    second time when the wall is already its own placement.
    """
    if p.element == "wire":
        xs = [q[0] for q in p.points]
        ys = [q[1] for q in p.points]
        return min(xs), min(ys), max(xs), max(ys)
    if p.symbol is not None:
        return S.box_bounds(p.at, p.symbol.ink, p.angle)
    if p.element == "ground":
        centre, half, angle = _wall_box(p)
        return S.box_bounds(centre, half, angle)
    if p.element == "phase":
        return S.box_bounds(*_phase_box(p))
    if p.element == "ellipsis":
        reach = ELLIPSIS_STEP + ELLIPSIS_R
        return S.box_bounds(p.at, (reach, ELLIPSIS_R), p.angle)
    if p.element == "anchor":
        # A label anchor draws nothing; the copies it speaks for are already
        # measured, and counting it again would pad the canvas.
        return p.at[0], p.at[1], p.at[0], p.at[1]
    r = p.radius
    return p.at[0] - r, p.at[1] - r, p.at[0] + r, p.at[1] + r


def compose(placements, size=None, padding=PADDING):
    """Everything a render works out, as a `Scene`.

    Wires come first so symbols sit over them, labels last so they sit over
    everything. Identical segments are drawn once: two branches sharing a
    trunk both route along it, and stroking it twice is waste.
    """
    wires, glyphs, nodes, labels = [], [], [], []
    rects, seen = [], set()
    # Both forms of every repeated group are drawn. The one that is not the
    # default goes into a hidden group with a stable id, so swapping between
    # them is two attribute flips rather than a rebuild — and because the
    # condensed form keeps the outermost copies, the two occupy the same
    # footprint and nothing re-fits.
    variants = collections.OrderedDict()

    def emit(p, markup, into):
        if p.variant is None:
            into.append(markup)
        else:
            bucket = variants.setdefault((p.ref, p.variant, p.shown), {})
            bucket.setdefault(p.copy, []).append(markup)

    for p in placements:
        if p.element != "wire":
            continue
        for seg in _segments([tuple(q) for q in p.points]):
            # Keyed per form, not globally. Both forms of a repeated group
            # share their trunks, and a global key gave the shared segment to
            # whichever form was emitted first — leaving the other drawn with
            # nothing joining it to its nodes.
            key = (_key(seg), p.variant)
            if key in seen or seg[0] == seg[1]:
                continue
            seen.add(key)
            emit(p, wire(seg), wires)

    for p in placements:
        if p.element == "symbol":
            emit(p, place(p.symbol, p.at[0], p.at[1], p.angle), glyphs)
        elif p.element == "ground":
            glyphs.append(ground(p.at[0], p.at[1], p.angle, *_wall(p)))
        elif p.element == "phase":
            glyphs.append(phase_mark(p.at[0], p.at[1]))
        elif p.element == "ellipsis":
            emit(p, ellipsis(p.at[0], p.at[1], p.angle), glyphs)
        elif p.element == "node":
            nodes.append(node(p.at[0], p.at[1], p.radius))

    # What is already on the page, so each label can avoid it. A label's own
    # symbol is registered against it as owner and skipped: clear_offset
    # solves that clearance, and solves it tighter than a bounding box can.
    occupied = S.Occupancy()
    for p in placements:
        if not p.shown:
            continue
        if p.element == "wire":
            for a, b in _segments([tuple(q) for q in p.points]):
                occupied.add_segment(a, b, owner=p)
        elif p.symbol is not None:
            occupied.add_box(p.at, (p.symbol.half_len, p.symbol.half),
                             p.angle, owner=p)
        elif p.element == "ground":
            # The boundary wall was the one drawn thing the solver could not
            # see, so a label was free to land on it.
            occupied.add_box(*_wall_box(p), owner=p)
        elif p.element == "phase":
            occupied.add_box(*_phase_box(p), owner=p)
        elif p.element == "node":
            occupied.add_box(p.at, (p.radius, p.radius), 0.0, owner=p)

    for p in placements:
        lab = p.label
        if lab is None:
            continue
        if not (lab.user or lab.value or lab.name or lab.extra):
            continue
        # The form that is not on show still gets its label drawn, into its
        # own hidden group, so it is there to fade in. It is solved against
        # the same occupancy — which holds the visible drawing — but it does
        # not join `rects`, because `check` and `describe` speak about what a
        # reader is actually looking at.
        report = {}
        # A form's label belongs to that form and fades with it. Putting the
        # visible one in the shared list left it stranded in the middle of the
        # other form when the two were swapped.
        into = [] if p.variant is not None else labels
        rect = S.annotate(p.at[0], p.at[1], p.angle, into, user=lab.user,
                          name=lab.name, value=lab.value,
                          extra=lab.extra,
                          half=lab.half, half_len=lab.half_len,
                          side=lab.side,
                          occupied=occupied if p.shown else None, owner=p,
                          report=report)
        if p.variant is not None:
            bucket = variants.setdefault((p.ref, p.variant, p.shown), {})
            bucket.setdefault(None, []).extend(into)
        if p.shown and rect:
            rects.append(LabelRect(rect, owner=p, report=report))

    parts = wires + glyphs + _variant_groups(variants) + nodes + labels
    ink = extent(placements, rects, 0.0)
    box = ((0.0, 0.0, float(size[0]), float(size[1])) if size is not None
           else extent(placements, rects, padding))
    return Scene(parts=parts, rects=rects, occupancy=occupied, ink=ink, box=box)


def draw(placements):
    """Markup and the rectangles the labels occupy — `compose`, in two parts.

    Kept because it is the published shape: `(parts, rects)`, where a rect
    unpacks as four numbers. `compose` is what to reach for when you also
    want to know why.
    """
    scene = compose(placements)
    return scene.parts, scene.rects


def extent(placements, rects, padding=PADDING):
    """What the drawing actually covers, labels included.

    Every placement is measured through `bounds`, which is anisotropic. This
    used to reserve `hypot(half_len, half)` in both directions — 44.9 around a
    conduction box that draws 16 tall — and a flat 30 around a boundary wall
    that draws 13 deep and only downward. The drawing then sat visibly high in
    its own frame, and the only way to find that out was to look at it.
    """
    xs, ys = [], []
    for p in placements:
        x0, y0, x1, y1 = bounds(p)
        xs += [x0, x1]
        ys += [y0, y1]
    for left, top, bw, bh in rects:
        xs += [left, left + bw]
        ys += [top, top + bh]
    if not xs:
        return 0.0, 0.0, 0.0, 0.0
    return (min(xs) - padding, min(ys) - padding,
            max(xs) + padding, max(ys) + padding)


def render(placements, size=None, padding=PADDING):
    """A complete SVG, sized to its contents unless told otherwise.

    `canvas` took dimensions the caller invented, and anything placed outside
    them was clipped with no warning at all. Measuring what was emitted
    removes the guess; passing `size` keeps the old behaviour.
    """
    scene = compose(placements, size, padding)
    body = "".join(scene.parts)
    if size is not None:
        return SY.canvas(size[0], size[1], body)
    x0, y0, x1, y1 = scene.box
    shifted = f'<g transform="translate({-x0:.1f},{-y0:.1f})">{body}</g>'
    return SY.canvas(round(x1 - x0, 1), round(y1 - y0, 1), shifted)
