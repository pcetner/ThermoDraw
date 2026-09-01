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


@dataclass
class Label:
    """What the solver needs to place one text block."""
    user: Optional[str] = None
    name: Optional[str] = None
    value: Optional[str] = None
    half: float = 5.5
    half_len: float = 5.5
    side: str = "auto"


@dataclass
class Placement:
    """One thing to draw, in page coordinates."""
    element: str                       # symbol | wire | node | ground
    at: Tuple[float, float] = (0.0, 0.0)
    angle: float = 0.0
    symbol: Optional[object] = None
    points: List[Sequence[float]] = field(default_factory=list)
    mirror: bool = False
    label: Optional[Label] = None
    radius: float = 5.5


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


def _rail_point(diagram, node_id, other):
    """Where a branch meets the rail: straight below the node it leaves."""
    return (other[0], diagram.rail.y)


def _endpoint(diagram, ref, other):
    if ref == M.RAIL:
        return _rail_point(diagram, ref, other)
    return tuple(diagram.node(ref).at)


def layout(diagram):
    """Placements for everything in the diagram, back to front."""
    diagram.validate()
    out = []

    for b in diagram.branches:
        sym = BY_KEY[b.kind]
        # the rail end depends on the other end, so resolve the node first
        if b.source == M.RAIL:
            target = _endpoint(diagram, b.target, (0, 0))
            source = _rail_point(diagram, b.source, target)
        else:
            source = _endpoint(diagram, b.source, (0, 0))
            target = _endpoint(diagram, b.target, source)
        route = [source] + [tuple(p) for p in b.via] + [target]

        index = _point_on(route, b.at) if b.at else _longest(route)
        a, c = route[index], route[index + 1]
        centre = tuple(b.at) if b.at else ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
        angle = b.angle if b.angle is not None else _angle(a, c)

        for run in _split(route, index, centre, sym.half_len):
            out.append(Placement("wire", points=run))
        out.append(Placement(
            "symbol", at=centre, angle=angle, symbol=sym,
            label=Label(user=b.label,
                        name=S.S_(M.BRANCH_SYMBOL[b.kind],
                                  M.BRANCH_SUB[b.kind]
                                  if M.BRANCH_SUB[b.kind] is not None
                                  else b.sub),
                        value=diagram.value_text(b.kind, b.value),
                        half=sym.half, half_len=sym.half_len,
                        side=b.side)))

    if diagram.rail:
        xs = [n.at[0] for n in diagram.nodes if n.at]
        span = diagram.rail.span or (min(xs), max(xs))
        out.append(Placement("wire", points=[(span[0], diagram.rail.y),
                                             (span[1], diagram.rail.y)]))

    for s in diagram.sources:
        sym = BY_KEY[s.kind]
        node = diagram.node(s.target)
        tip = tuple(node.at)
        centre = tuple(s.at) if s.at else (
            tip[0] - (sym.half_len + 5.5), tip[1])
        angle = s.angle
        out.append(Placement(
            "symbol", at=centre, angle=angle, symbol=sym,
            label=Label(user=s.label,
                        name=S.S_(M.SOURCE_SYMBOL[s.kind], s.sub),
                        value=diagram.value_text(s.kind, s.value),
                        half=sym.half, half_len=sym.half_len,
                        side=s.side)))
        rad = math.radians(angle)
        head = (centre[0] + math.cos(rad) * sym.half_len,
                centre[1] + math.sin(rad) * sym.half_len)
        edge = (tip[0] - math.cos(rad) * 5.5, tip[1] - math.sin(rad) * 5.5)
        if _length(head, edge) > 0.5:
            out.append(Placement("wire", points=[head, edge]))

    for n in diagram.nodes:
        if n.kind == "corner":
            continue
        at = tuple(n.at)
        # A fixed node reaches down to its boundary wall, so the label has to
        # clear the wall and not just the circle. The extents live on the
        # Symbol, which is what they are for.
        sym = BY_KEY.get(n.kind)
        half = sym.half if sym else 5.5
        half_len = sym.half_len if sym else 5.5
        out.append(Placement(
            "node", at=at, angle=n.angle,
            label=Label(user=n.label, name=S.S_("T", n.sub),
                        value=diagram.value_text(n.kind, n.value),
                        half=half, half_len=half_len,
                        side=n.side)))
        if n.kind == "fixed":
            out.append(Placement("wire", points=[at, (at[0], at[1] + 12)]))
            out.append(Placement("ground", at=(at[0], at[1] + 12), angle=90))
    return out
