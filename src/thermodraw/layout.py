"""Turning a diagram into placements.

Pure: a `Diagram` in, a list of `Placement` out, no SVG and no globals. This
is the one stage the network layer replaces. Today it reads the coordinates
you supplied and works out the wire runs between them; in 0.3 it will solve
for the coordinates you left out. Nothing either side of it needs to change.

A branch is routed as `[source, *via, target]`. The symbol sits at `at`, or at
the midpoint of the longest straight segment, and the wire is interrupted
either side of it by the symbol's own half-length. Waypoints are how a
parallel path is expressed until the router can find one for itself.
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from . import model as M
from . import symbols as S

BY_KEY = {s.key: s for s in S.SYMBOLS}

# `break` is both a node kind and a branch kind — the same thing in two
# positions, which is a feature for whoever writes the JSON. It is a collision
# in here, because BY_KEY is one namespace, so the branch resolves through
# this and the node goes straight to BY_KEY.
BRANCH_SYM = {"break": "break-branch", "flow": "flow-branch"}

# How a node meets its boundary. A fixed node reaches down STUB units to its
# wall; a thermal break stops at the circle and its wall stands BREAK_GAP away,
# with nothing in between. BREAK_WALL is g_break's own (half, depth), not the
# one render.ground defaults to — the two symbols are drawn at different
# scales, and docs/symbol-reference.html is the record for that one.
STUB = 12
BREAK_GAP = 24
BREAK_WALL = (22, 13)


@dataclass
class Label:
    """What the solver needs to place one text block."""
    user: Optional[str] = None
    name: Optional[str] = None
    value: Optional[str] = None
    extra: Sequence[str] = ()
    half: float = 5.5
    half_len: float = 5.5
    side: str = "auto"


@dataclass
class Placement:
    """One thing to draw, in page coordinates.

    `ref` names what in the diagram produced this — "node 'j'",
    "branch 2 j->c", "source 0 -> j", "rail". Everything a branch emits shares
    one ref, lead wires included, which is what lets a diagnostic say "this
    label is nearer that branch than the node it names" without counting the
    node's own stub as a stranger.

    It is a string rather than the model object on purpose: holding a `Node`
    would alias mutable state into a documented-pure output and change what
    two placements comparing equal means. It is derived from position for
    branches and sources, because neither has an id in the schema, so it is
    not stable under reordering. It is a diagnostic, not a key.
    """
    element: str                       # symbol | wire | node | ground
    at: Tuple[float, float] = (0.0, 0.0)
    angle: float = 0.0
    symbol: Optional[object] = None
    points: List[Sequence[float]] = field(default_factory=list)
    label: Optional[Label] = None
    radius: float = 5.5
    ref: Optional[str] = None
    wall: Optional[Tuple[float, float]] = None   # (half, depth) of a ground


def _angle(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _length(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _point_on(route, at):
    """Which segment of the route carries `at`, and how far along it."""
    best, best_d = 0, None
    for i in range(len(route) - 1):
        a, b = route[i], route[i + 1]
        seg = _length(a, b)
        if not seg:
            continue
        t = (((at[0] - a[0]) * (b[0] - a[0]) + (at[1] - a[1]) * (b[1] - a[1]))
             / (seg * seg))
        t = max(0.0, min(1.0, t))
        near = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        d = _length(at, near)
        if best_d is None or d < best_d:
            best, best_d = i, d
    return best


def _longest(route):
    lengths = [_length(route[i], route[i + 1]) for i in range(len(route) - 1)]
    return lengths.index(max(lengths))


def _split(route, index, centre, half_len):
    """The route with a gap of 2*half_len cut out around `centre`."""
    a, b = route[index], route[index + 1]
    seg = _length(a, b) or 1.0
    ux, uy = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
    before = list(route[:index + 1]) + [
        (centre[0] - ux * half_len, centre[1] - uy * half_len)]
    after = [(centre[0] + ux * half_len, centre[1] + uy * half_len)] + \
        list(route[index + 1:])
    return [p for p in (before, after) if len(p) > 1]


def _source_offset(sym):
    """How far from its node a source sits when the author gave no `at`.

    The default was `half_len + 5.5`, which considers only how long the
    symbol is and never how tall. That suits the three arrow kinds, which are
    long and thin. `flux` is a 52 x 48 block, and at that offset it blocked
    the node's label from below while the source's own label blocked it from
    above — both candidate sides gone, so `annotate` pushed the node's label
    out instead of flipping it, and the checker called it adrift.

    No constant can be universally right here. Whether a label fits depends
    on how wide it is, and labels are not solved until `render`. This buys
    room in proportion to how much of the node's neighbourhood the symbol
    occupies, and leaves the arrows exactly where they were.
    """
    return sym.half_len + 5.5 + max(0.0, 2 * (sym.half - 7))


def _rail_point(diagram, node_id, other):
    """Where a branch meets the rail: straight below wherever it came from.

    `other` is the last waypoint if the branch has any, and the node itself
    otherwise. It used to be the node either way, which made
    `docs/schema.md`'s promise — that waypoints on a capacitance are "how you
    free up the space directly under a node that already has too much
    attached to it" — false: the route detoured and came back to the same
    place. Buying a 480-unit diagonal for nothing cost one reader a full
    re-layout.
    """
    return (other[0], diagram.rail.y)


def _endpoint(diagram, ref, other):
    if ref == M.RAIL:
        return _rail_point(diagram, ref, other)
    return tuple(diagram.node(ref).at)


def layout(diagram):
    """Placements for everything in the diagram, back to front."""
    diagram.validate()
    out = []

    for i, b in enumerate(diagram.branches):
        ref = f"branch {i} {b.source}->{b.target}"
        sym = BY_KEY[BRANCH_SYM.get(b.kind, b.kind)]
        # the rail end depends on the other end, so resolve the node first
        if b.source == M.RAIL:
            target = _endpoint(diagram, b.target, (0, 0))
            near = tuple(b.via[0]) if b.via else target
            source = _rail_point(diagram, b.source, near)
        else:
            source = _endpoint(diagram, b.source, (0, 0))
            near = tuple(b.via[-1]) if b.via else source
            target = _endpoint(diagram, b.target, near)
        route = [source] + [tuple(p) for p in b.via] + [target]

        index = _point_on(route, b.at) if b.at else _longest(route)
        a, c = route[index], route[index + 1]
        centre = tuple(b.at) if b.at else ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
        angle = b.angle if b.angle is not None else _angle(a, c)

        for run in _split(route, index, centre, sym.half_len):
            out.append(Placement("wire", points=run, ref=ref))
        # A break names no quantity, so it gets no second line rather than an
        # invented symbol for a resistance it does not have.
        base = M.BRANCH_SYMBOL[b.kind]
        sub = (M.BRANCH_SUB[b.kind] if M.BRANCH_SUB[b.kind] is not None
               else b.sub)
        out.append(Placement(
            "symbol", at=centre, angle=angle, symbol=sym, ref=ref,
            label=Label(user=b.label,
                        name=S.S_(base, sub) if base else None,
                        value=diagram.value_text(b.kind, b.value),
                        extra=[x for x in (
                            diagram.rate_text(b.rate),
                            diagram.count_text(b.count, b.arrangement)) if x],
                        half=sym.half, half_len=sym.half_len,
                        side=b.side)))

    if diagram.rail:
        xs = [n.at[0] for n in diagram.nodes if n.at]
        span = diagram.rail.span or (min(xs), max(xs))
        out.append(Placement("wire", ref="rail",
                             points=[(span[0], diagram.rail.y),
                                     (span[1], diagram.rail.y)]))

    for i, s in enumerate(diagram.sources):
        ref = (f"source {i} {s.source} ->" if s.outward
               else f"source {i} -> {s.target}")
        sym = BY_KEY[s.kind]
        node = diagram.node(s.node)
        tip = tuple(node.at)
        # Direction is which end of the arrow meets the node, and nothing
        # else. Every source glyph draws its tail at -half_len and its head
        # at +half_len, so `from` and `to` share one drawing at one rotation:
        # put the symbol on the far side and join the head, or on the near
        # side and join the tail. On `flux` that is the whole feature — the
        # hatch band is a surface, so joining the tail stands the surface
        # against the node with the arrows leaving it.
        rad = math.radians(s.angle)
        along = (math.cos(rad), math.sin(rad))
        step = _source_offset(sym) * (1 if s.outward else -1)
        centre = tuple(s.at) if s.at else (tip[0] + along[0] * step,
                                           tip[1] + along[1] * step)
        out.append(Placement(
            "symbol", at=centre, angle=s.angle, symbol=sym, ref=ref,
            label=Label(user=s.label,
                        name=S.S_(M.SOURCE_SYMBOL[s.kind], s.sub),
                        value=diagram.value_text(s.kind, s.value),
                        extra=[x for x in
                               (diagram.count_text(s.count, "parallel"),) if x],
                        half=sym.half, half_len=sym.half_len,
                        side=s.side)))
        reach = -sym.half_len if s.outward else sym.half_len
        end = (centre[0] + along[0] * reach, centre[1] + along[1] * reach)
        edge = (tip[0] + along[0] * (5.5 if s.outward else -5.5),
                tip[1] + along[1] * (5.5 if s.outward else -5.5))
        if _length(end, edge) > 0.5:
            out.append(Placement("wire", points=[end, edge], ref=ref))

    for n in diagram.nodes:
        if n.kind == "corner":
            continue
        ref = f"node '{n.id}'"
        at = tuple(n.at)
        # A fixed node reaches down to its boundary wall, so the label has to
        # clear the wall and not just the circle. The extents live on the
        # Symbol, which is what they are for.
        sym = BY_KEY.get(n.kind)
        half = sym.half if sym else 5.5
        half_len = sym.half_len if sym else 5.5
        # `T` with no number after it is not a statement about anything, and
        # interior junctions between series layers routinely have no
        # temperature of their own. It rendered as a lone italic T and the
        # checker said nothing, so two readers fell back to `corner`, which
        # draws nothing and loses the name. A subscript is enough to make it
        # meaningful — a diagram may be symbolic throughout — but a bare T
        # is not.
        names = n.value is not None or bool(n.sub)
        out.append(Placement(
            "node", at=at, angle=n.angle, ref=ref,
            label=Label(user=n.label,
                        name=S.S_("T", n.sub) if names else None,
                        value=diagram.value_text(n.kind, n.value),
                        half=half, half_len=half_len,
                        side=n.side)))
        # Both boundary kinds draw a wall; only one draws the stub reaching
        # it. That gap is the entire distinction between them, and it is
        # topological rather than decorative — which is why `break` having
        # quietly emitted nothing but a bare circle was a bug and not a
        # missing flourish. `g_break` was unreachable from the data pipeline.
        if n.kind == "fixed":
            out.append(Placement("wire", points=[at, (at[0], at[1] + STUB)],
                                 ref=ref))
            out.append(Placement("ground", at=(at[0], at[1] + STUB), angle=90,
                                 ref=ref))
        elif n.kind == "phase":
            out.append(Placement("phase", at=at, ref=ref))
        elif n.kind == "break":
            # Set further out than a fixed node's wall, so the clear space
            # reads as longer than a stub. At the stub's own distance the
            # reader is left wondering whether the stub failed to draw.
            out.append(Placement("ground", at=(at[0], at[1] + BREAK_GAP),
                                 angle=90, ref=ref, wall=BREAK_WALL))
    return out
