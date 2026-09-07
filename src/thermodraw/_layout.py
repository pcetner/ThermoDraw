"""Turning a diagram into placements.

Pure: a `Diagram` in, a list of `Placement` out, no SVG and no globals. This
is the seam the network layer sits at. It reads the coordinates you supplied
and works out the wire runs between them; the coordinates you left out are
solved first by `_solve`, for a chain of nodes, on a copy. A general placer
would replace that pre-pass and nothing either side of it.

A branch is routed as `[source, *via, target]`. The symbol sits at `at`, or at
the midpoint of the longest straight segment, and the wire is interrupted
either side of it by the symbol's own half-length. Waypoints are how a
parallel path is expressed until the router can find one for itself.
"""
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from . import _solve
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

# Which way the wall faces: the unit step from the node to where the wall
# stands, and the angle `render.ground` lays the hatch at so that it hangs
# off the far side. `down` is the drawing every diagram before 1.0 had. The
# other three exist because a mount that holds a cold mass from above has
# its wall above, and the third clean-room run could not draw that: with the
# wall always below, the strut left through the mount's own hatching.
WALL = {"down": ((0, 1), 90), "up": ((0, -1), 270),
        "left": ((-1, 0), 180), "right": ((1, 0), 0)}


@dataclass
class Label:
    """What the solver needs to place one text block."""
    user: Optional[str] = None
    name: Optional[str] = None
    value: Optional[str] = None
    # Prose, or a `(symbol, value)` pair written like the value line.
    extra: Sequence[Union[str, Sequence[str]]] = ()
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
    # `S.Symbol`, not `object`: it was loose enough that `p.symbol.key`
    # could not be checked anywhere, and `symbols` imports nothing
    # from here, so naming the real type costs no cycle.
    symbol: Optional[S.Symbol] = None
    points: List[Sequence[float]] = field(default_factory=list)
    label: Optional[Label] = None
    radius: float = 5.5
    ref: Optional[str] = None
    # (half, depth) for a ground; (span, length) for an elision mark
    wall: Optional[Tuple[float, float]] = None
    # Which copy of a repeated branch this is, and which form it belongs to:
    # None is drawn either way, "full" is dropped when condensed, "condensed"
    # is the ellipsis that stands in its place.
    copy: Optional[int] = None
    variant: Optional[str] = None
    # False for the form that is not the default. It is still drawn, into a
    # hidden group, so a viewer can swap without the diagram being rebuilt.
    shown: bool = True
    # What in the diagram this came from, as data rather than as a string to
    # parse back out of `ref`: "branch", "source", "node" or "rail", and the
    # ids at its ends — (source, target) for a branch, (node_id,) for a source
    # or a node, () for the rail. `check` and `describe` read these. `ref` is
    # for people, and a node called `a->b` used to break both of them.
    role: Optional[str] = None
    ends: Tuple[str, ...] = ()
    # The rest of what a remedy has to know before it can name a field, and
    # what `describe` prints beside an edge. A remedy once said "move a `via`
    # waypoint" on a branch that had none, and on a repeated branch, which
    # the validator refuses `via` on — the checker could not tell, because
    # the placement did not carry it. `via` is the branch's waypoints;
    # `count` and `arrangement` are the group a branch or source stands for;
    # `outward` is whether a source's heat leaves its node.
    via: Tuple[Tuple[float, float], ...] = ()
    count: Optional[int] = None
    arrangement: Optional[str] = None
    outward: Optional[bool] = None
    # Where in the diagram's own list the element sits: `nodes[index]`,
    # `branches[index]` or `sources[index]`, by `role`. `ref` carries the
    # same number for a branch, but as prose, and a pair of branches
    # between one node pair share everything else a placement says about
    # them. An editor that maps a click back to a field needs the number
    # as a number. None on the rail.
    index: Optional[int] = None


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


# ------------------------------------------------------- repeated branches
# `count` says there are several identical paths, and the drawing shows them.
#
# Each form is a *complete* drawing of the group — its own copies, its own
# wire, its own label — and they are independently centred, so the condensed
# form is genuinely smaller rather than the full one with holes in it. That is
# what lets a page shrink and expand it: `render` writes both extents, and the
# viewer tweens the canvas between them while the two forms cross-fade.
#
# It costs the property the first design had, where both forms shared a
# footprint and nothing ever moved. Shrinking is worth more: a group of
# sixteen condensed to two should take the room of two.
TRUNK = 64        # clean wire out of a node before the riser, so a
                  # node's own label is not crossed by it
PITCH_PAD = 14    # clear space between adjacent parallel lanes
SERIES_PAD = 18   # clear space between symbols set end to end
ELLIPSIS_STEP = 9


def _lanes(a, b, offsets):
    """One route per lane, at each perpendicular offset from the line a-b.

    A trunk out of each node, a riser square across it, then the lane. Right
    angles throughout: the first version fanned out diagonally, which reads as
    janky at any lane count above about four and gets worse as the fan grows.
    A comb is what this is drawn as by hand, and every lane's riser sits on
    the same line, so the branch point is a single visible junction rather
    than a spray.

    The trunk is what keeps the risers off the nodes. Lanes leaving straight
    from a node cross the space its own label wants, and every default-placed
    group reported `label-adrift` until it was added. Both trunks dedupe,
    being one segment shared by every lane.
    """
    span = _length(a, b) or 1.0
    ux, uy = (b[0] - a[0]) / span, (b[1] - a[1]) / span
    nx, ny = -uy, ux
    trunk = min(TRUNK, span / 6)
    jin = (a[0] + ux * trunk, a[1] + uy * trunk)
    jout = (b[0] - ux * trunk, b[1] - uy * trunk)
    for off in offsets:
        head = (jin[0] + nx * off, jin[1] + ny * off)
        tail = (jout[0] + nx * off, jout[1] + ny * off)
        yield [a, jin, head, tail, jout, b], ((head[0] + tail[0]) / 2,
                                              (head[1] + tail[1]) / 2)


def _along(a, b, centre, offsets):
    """Points at each offset along the line a-b, measured from `centre`."""
    span = _length(a, b) or 1.0
    ux, uy = (b[0] - a[0]) / span, (b[1] - a[1]) / span
    return [(centre[0] + ux * d, centre[1] + uy * d) for d in offsets]


def _series_runs(a, b, centres, half_len):
    """The wire either side of, and between, symbols set end to end."""
    span = _length(a, b) or 1.0
    ux, uy = (b[0] - a[0]) / span, (b[1] - a[1]) / span

    def edge(p, sign):
        return (p[0] + ux * half_len * sign, p[1] + uy * half_len * sign)

    runs = [[a, edge(centres[0], -1)]]
    for i in range(len(centres) - 1):
        runs.append([edge(centres[i], 1), edge(centres[i + 1], -1)])
    runs.append([edge(centres[-1], 1), b])
    return [r for r in runs if _length(r[0], r[1]) > 0.5]


def _centred(n, pitch):
    """`n` offsets of `pitch`, centred on zero."""
    return [(k - (n - 1) / 2) * pitch for k in range(n)]


def _form(b, ref, sym, source, target, centre, angle, label, n, variant,
          shown, index=None):
    """One complete drawing of a repeated group: copies, wire, label, dots."""
    out = []
    tag = {"variant": variant, "shown": shown,
           "role": "branch", "ends": (b.source, b.target),
           "count": b.count, "arrangement": b.arrangement, "index": index}
    dots = variant == "condensed"

    if b.arrangement == "series":
        pitch = 2 * sym.half_len + SERIES_PAD
        gap = 2 * sym.half_len + 2 * ELLIPSIS_STEP + 22
        offsets = ([-gap / 2, gap / 2] if dots else _centred(n, pitch))
        spots = _along(source, target, centre, offsets)
        for run in _series_runs(source, target, spots, sym.half_len):
            out.append(Placement("wire", points=run, ref=ref, **tag))
        for k, c in enumerate(spots):
            out.append(Placement("symbol", at=c, angle=angle, symbol=sym,
                                 ref=ref, copy=k, **tag))
        reach = (abs(offsets[0]) + sym.half_len, sym.half)
    else:
        pitch = 2 * sym.half + PITCH_PAD
        offsets = [-pitch / 2, pitch / 2] if dots else _centred(n, pitch)
        for k, (route, c) in enumerate(_lanes(source, target, offsets)):
            for run in _split(route, 2, c, sym.half_len):
                out.append(Placement("wire", points=run, ref=ref, copy=k,
                                     **tag))
            out.append(Placement("symbol", at=c, angle=angle, symbol=sym,
                                 ref=ref, copy=k, **tag))
        reach = (sym.half_len, abs(offsets[0]) + sym.half)

    if dots:
        # Along the branch either way. An ellipsis means "and more of these"
        # in the direction it runs, so it reads as an omission rather than as
        # a decoration — which is what stacking it across the lanes looked
        # like.
        out.append(Placement("ellipsis", at=centre, angle=angle, ref=ref,
                             **tag))

    # Each form carries its own label, solved against its own extent, so a
    # condensed group's text sits against the two copies it shows rather than
    # against the sixteen it does not. They cross-fade with the drawing.
    own = Label(user=label.user, name=label.name, value=label.value,
                extra=list(label.extra), half=reach[1], half_len=reach[0],
                side=label.side)
    out.append(Placement("anchor", at=centre, angle=angle, ref=ref,
                         radius=0.0, label=own, **tag))
    return out


def _repeat(b, ref, sym, source, target, centre, angle, label, index=None):
    """Both forms of a repeated branch, one shown and one hidden.

    Above `CONDENSE_ABOVE` the condensed form is the default. At or below it
    every copy is drawn and there is no second form to swap to, so nothing is
    hidden and no control is offered.
    """
    n, condensed = b.count, b.condensed
    if not condensed:
        return _form(b, ref, sym, source, target, centre, angle, label, n,
                     None, True, index)
    return (_form(b, ref, sym, source, target, centre, angle, label, n,
                  "full", False, index)
            + _form(b, ref, sym, source, target, centre, angle, label, 2,
                    "condensed", True, index))


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


def layout(diagram) -> List[Placement]:
    """Placements for everything in the diagram, back to front.

    Nodes without `at` are placed first by `_solve`, on a copy; a diagram
    with every node placed goes through untouched.
    """
    diagram.validate()
    diagram = _solve.solve(diagram)
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

        # A break names no quantity, so it gets no second line rather than an
        # invented symbol for a resistance it does not have.
        base = M.BRANCH_SYMBOL[b.kind]
        sub = (M.BRANCH_SUB[b.kind] if M.BRANCH_SUB[b.kind] is not None
               else b.sub)
        # A rate is written `q = 12 W`, not `12 W`. It is a quantity, and
        # every quantity on the page is stated with its own symbol; without
        # one it reads as a second, unexplained number under the resistance.
        rate = diagram.rate_text(b.rate)
        label = Label(user=b.label,
                      name=S.S_(base, sub) if base else None,
                      value=diagram.value_text(b.kind, b.value),
                      extra=[x for x in (
                          (S.S_(M.RATE), rate) if rate else None,
                          diagram.count_text(b.count, b.arrangement,
                                             b.kind, b.value)) if x],
                      half=sym.half, half_len=sym.half_len,
                      side=b.side)
        if b.repeated:
            out += _repeat(b, ref, sym, source, target, centre, angle, label,
                           index=i)
            continue
        # `Dict[str, Any]`, and it has to be. These are the
        # provenance fields spread into every `Placement` for
        # one element, and they are heterogeneous by design:
        # a role, a tuple of ends, a count, a flag. mypy
        # cannot check a `**` spread of a heterogeneous dict
        # against a dataclass, and pretending otherwise cost
        # 87 of the 91 errors the public annotations
        # surfaced.
        who: Dict[str, Any] = {"role": "branch", "ends": (b.source, b.target),
               "via": tuple(tuple(p) for p in b.via), "index": i}
        for run in _split(route, index, centre, sym.half_len):
            out.append(Placement("wire", points=run, ref=ref, **who))
        out.append(Placement(
            "symbol", at=centre, angle=angle, symbol=sym, ref=ref,
            label=label, **who))

    if diagram.rail:
        xs = [n.at[0] for n in diagram.nodes if n.at]
        span = diagram.rail.span or (min(xs), max(xs))
        out.append(Placement("wire", ref="rail", role="rail",
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
        who = {"role": "source", "ends": (s.node,), "outward": s.outward,
               "count": s.count, "index": i}
        out.append(Placement(
            "symbol", at=centre, angle=s.angle, symbol=sym, ref=ref,
            label=Label(user=s.label,
                        name=S.S_(M.SOURCE_SYMBOL[s.kind], s.sub),
                        value=diagram.value_text(s.kind, s.value),
                        extra=[x for x in
                               (diagram.source_count_text(
                                   s.count, s.kind, s.value),) if x],
                        half=sym.half, half_len=sym.half_len,
                        side=s.side), **who))
        reach = -sym.half_len if s.outward else sym.half_len
        end = (centre[0] + along[0] * reach, centre[1] + along[1] * reach)
        # The wire stops on the node's circle rather than at its centre, and
        # the 5.5 is measured along the wire's own direction, `tip` towards
        # `end`. It used to be measured along `angle`, which is the same
        # vector only while the source stands on its node's axis — which is
        # where the solver puts one, and where an author writing `at` by hand
        # mostly put one. A source dragged off that axis in the editor keeps
        # its `angle`, so the trim went sideways: an arrow at angle 270 set
        # to the left of its node ended 5.5 straight *down* from the centre,
        # off its own line and on the fixed node's stub, hidden under the
        # circle's opaque fill. The wire read as stopping short of the node
        # it joins.
        span = _length(end, tip)
        if span > 5.5 + 0.5:
            ux, uy = (end[0] - tip[0]) / span, (end[1] - tip[1]) / span
            edge = (tip[0] + ux * 5.5, tip[1] + uy * 5.5)
            out.append(Placement("wire", points=[end, edge], ref=ref, **who))

    for i, n in enumerate(diagram.nodes):
        ref = f"node '{n.id}'"
        at = tuple(n.at)
        # A fixed node reaches down to its boundary wall, so the label has to
        # clear the wall and not just the circle. The extents live on the
        # Symbol, which is what they are for.
        glyph = BY_KEY.get(n.kind)
        half = glyph.half if glyph else 5.5
        half_len = glyph.half_len if glyph else 5.5
        (dx, dy), wall_angle = WALL[n.wall]
        if dx:
            # The Symbol's extents are for a wall below: `half` is what
            # clears it, across the label frame. Turned sideways the wall
            # is along the frame instead, so the two clearances swap.
            half, half_len = half_len, half
        # `T` with no number after it is not a statement about anything, and
        # interior junctions between series layers routinely have no
        # temperature of their own. It rendered as a lone italic T and the
        # checker said nothing, so two readers fell back to `corner` (a kind
        # since removed), which drew nothing and lost the name. A subscript is enough to make it
        # meaningful — a diagram may be symbolic throughout — but a bare T
        # is not.
        names = n.value is not None or bool(n.sub)
        who = {"role": "node", "ends": (n.id,), "index": i}
        # The automatic side is above, and with the wall below that is
        # away from it. With the wall above, away is below: a label that
        # took the automatic side would sit beyond the hatching, which is
        # what `side` toward the wall asks for and the default should not.
        # Preferred, not forced — the branch that made the wall face up is
        # usually the one arriving from below, and then the label steps
        # back above, beyond the wall, as the fallback.
        side = n.side
        if side == "auto" and n.wall == "up" and n.angle % 180 == 0:
            side = "auto:down"
        out.append(Placement(
            "node", at=at, angle=n.angle, ref=ref,
            label=Label(user=n.label,
                        name=S.S_("T", n.sub) if names else None,
                        value=diagram.value_text(n.kind, n.value),
                        half=half, half_len=half_len,
                        side=side), **who))
        # Both boundary kinds draw a wall; only one draws the stub reaching
        # it. That gap is the entire distinction between them, and it is
        # topological rather than decorative — which is why `break` having
        # quietly emitted nothing but a bare circle was a bug and not a
        # missing flourish. `g_break` was unreachable from the data pipeline.
        if n.kind == "fixed":
            foot = (at[0] + dx * STUB, at[1] + dy * STUB)
            out.append(Placement("wire", points=[at, foot], ref=ref, **who))
            out.append(Placement("ground", at=foot, angle=wall_angle,
                                 ref=ref, **who))
        elif n.kind == "phase":
            out.append(Placement("phase", at=at, ref=ref, **who))
        elif n.kind == "break":
            # Set further out than a fixed node's wall, so the clear space
            # reads as longer than a stub. At the stub's own distance the
            # reader is left wondering whether the stub failed to draw.
            out.append(Placement(
                "ground", at=(at[0] + dx * BREAK_GAP, at[1] + dy * BREAK_GAP),
                angle=wall_angle, ref=ref, wall=BREAK_WALL, **who))
    return out


# ---------------------------------------------------------------- topology
# The network as nodes joined by branches, read off the placements. `check`
# asks it whether the drawing is one piece and `describe` prints it; they
# used to build it separately, one parsing `ref` strings, and `describe`'s
# docstring promised the two could not disagree. Now they cannot.
def network(placements):
    """`(source, target, kind)` per branch, in diagram order, as written.

    One entry per branch, not per placement: a branch emits several — wire
    runs, its symbol, a repeated group's copies — and they share a `ref`.
    """
    kinds = {sym: kind for kind, sym in BRANCH_SYM.items()}
    seen, edges = set(), []
    for p in placements:
        if p.role != "branch" or p.symbol is None or p.ref in seen:
            continue
        seen.add(p.ref)
        # The kind as the author wrote it, not the symbol that draws it:
        # `flow`, not `flow-branch`.
        edges.append((p.ends[0], p.ends[1],
                      kinds.get(p.symbol.key, p.symbol.key)))
    return edges


def pieces(edges, ids):
    """`ids` grouped into connected components, largest first, each sorted.

    An endpoint that is not in `ids` — the rail — still joins what it
    touches, so two capacitances dropping to one rail are one piece.
    """
    adj: Dict[str, Set[str]] = {i: set() for i in ids}
    for a, b, _ in edges:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    seen, groups = set(), []
    for start in sorted(adj):
        if start in seen:
            continue
        stack, group = [start], set()
        while stack:
            v = stack.pop()
            if v in group:
                continue
            group.add(v)
            stack += [w for w in adj[v] if w not in group]
        seen |= group
        groups.append(sorted(group))
    return sorted(groups, key=lambda g: (-len(g), g))
