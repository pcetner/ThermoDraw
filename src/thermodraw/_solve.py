"""Coordinates for the nodes you left out: the ladder solver.

`solve(diagram)` returns a diagram in which every node has `at`. Nodes that
had one keep it; the rest are placed on one line, heat running left to
right, at the spacing `docs/schema.md` has always recommended as a habit.
The input is never touched: this is a pre-pass on a copy, so `layout`,
`describe` and `to_dict` all see the solved numbers and nothing either side
of it changes.

What it solves is a ladder — a chain of nodes joined by branches, each node
with at most two neighbours — because that is what nearly every thermal
resistance network drawn in this notation is, and it is the shape a solver
can place without an objective: rank along the chain gives x, the main line
gives y, and a pair of branches between the same two nodes goes above and
below. Anything that is not a chain is refused, naming the node that joins
three others, so the author gives that node `at` and the drawing is never
silently bad. A general placer is the network layer proper; the record's
table of what survives it says which checks it must satisfy. This one
satisfies them by construction on the shape it accepts.

A source without `at` is placed half a pitch out along its `angle`, which
is where the hero's authors put theirs; `layout`'s own default of a few
units past the arrow is for a hand-placed drawing and is unchanged. `angle`
0 is both "unset" and "from the left", and on the main line "from the left"
is the branch, so an angle-0 source on any node but the hot end is turned to
arrive from above — or, leaving, to leave downward — and a node with a lead
above it and a wire below it, a capacitance or a leaving source, has its
label frame turned to 45, the one direction that clears the lead, the wire
and the run. A repeated
branch draws a comb that stands off its own nodes and refuses `via`, so
there is nothing to route; a plain branch round it goes far enough out to
clear its lanes.
"""
import copy
import math
from typing import Dict, List, Optional, Set

from . import model as M

# The habit, as numbers. `docs/schema.md` gave them as advice — "space
# nodes about 220 apart and put parallel paths 80 above and below the main
# line" — and every diagram in the gallery that followed it checked clean.
X0, Y0, PITCH = 200, 150, 220
# A parallel pair leaves and arrives sideways rather than straight up out
# of a node: straight up puts the wire where the node's own label wants to
# sit, and straight down onto a boundary puts it through the wall. Run 3's
# three `wire-through-wall` defects all arrived at the node.
OFF, LEAD = 80, 48
# A source's own label is as wide as a node's, so it needs the room a node
# gets. `layout` defaults to 37.5 for a diss arrow, which put the hero's
# source label over the room its junction label needed and pushed the
# junction 36 past its clearance; the hero's authors used 104.
SOURCE = PITCH / 2
# Air between the labels on one run, at each end: the gap the label solver
# keeps between a block and the symbol it belongs to.
SLACK = 5


def _num(value) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _neighbours(diagram) -> Dict[str, Set[str]]:
    """Who is joined to whom by a branch, the rail and sources left out."""
    joined: Dict[str, Set[str]] = {n.id: set() for n in diagram.nodes}
    for b in diagram.branches:
        if M.RAIL in (b.source, b.target):
            continue
        joined[b.source].add(b.target)
        joined[b.target].add(b.source)
    return joined


def _chain(diagram) -> List[str]:
    """The nodes in order from the hot end, or a DiagramError saying why not.

    A chain: connected, and no node joined to three others. The hot end is
    the end with the higher stated temperature; failing numbers, the end a
    source arrives at; failing that, the one written first. Temperature
    picks the end and only the end — sorting a whole chain by temperature
    would interleave a heater in the middle of a ladder and cross its wires.
    """
    joined = _neighbours(diagram)
    order = [n.id for n in diagram.nodes]
    for node in order:
        if len(joined[node]) > 2:
            others = ", ".join(repr(o) for o in sorted(joined[node]))
            # "Give node 'x' `at`" was the remedy here, and it did not
            # apply: one unplaced node anywhere sends the whole file to
            # this test, so a clean-room reader gave the named node `at`,
            # then `via` as well, and got the same message back twice.
            # What clears it is placing every node, and the message says
            # that. Placing part of a non-chain is the general placer.
            raise M.DiagramError(
                f"node {node!r} joins {len(joined[node])} others ({others}); "
                "the solver places a chain, so give every node `at` "
                "yourself, and `via` on the branches that leave "
                f"node {node!r} sideways")
    if not order:
        return []
    ends = [n for n in order if len(joined[n]) <= 1]
    if not ends:                         # every node has two neighbours
        first = order[0]
        raise M.DiagramError(
            f"the nodes form a loop through node {first!r}; the solver "
            "places a chain, so give every node `at` yourself")

    def temperature(node):
        return _num(diagram.node(node).value)

    def fed(node):
        return any(s.target == node for s in diagram.sources)

    hot = max(ends, key=lambda n: (
        temperature(n) if temperature(n) is not None else float("-inf"),
        fed(n), -order.index(n)))
    walk, seen = [hot], {hot}
    while True:
        here = walk[-1]
        step = [n for n in joined[here] if n not in seen]
        if not step:
            break
        walk.append(step[0])
        seen.add(step[0])
    if len(walk) != len(order):
        left = next(n for n in order if n not in seen)
        raise M.DiagramError(
            f"node {left!r} has no path of branches to node {hot!r}; the "
            "solver places one chain, so join it, or give every node in "
            "its piece `at` yourself")
    return walk


def solve(diagram):
    """The diagram with every node placed. A copy; the input is untouched.

    A diagram with every `at` already given is returned as it is, so the
    ordinary case pays nothing. Otherwise every node without `at` is placed
    along the chain from the hot end, each run as wide as the labels on it
    need and never narrower than the habit's pitch. Explicit nodes keep
    their place and the next solved node is measured from them, so a partly
    placed ladder that follows the habit slots in and one that does not is
    the author's to reconcile — `check` says where.

    Two passes. The first places at the habit's pitch and lays the result
    out, which is the only way to learn how wide each label is: widths come
    from the same solver and metrics the renderer uses, through `compose`,
    so what is measured is what will be drawn. The second places again from
    a fresh copy with each run widened to what its labels came to, which is
    the arithmetic `nodes-too-close` reports — half of each node's label and
    all of the branch's — done before the drawing rather than after.
    """
    if all(n.at is not None for n in diagram.nodes):
        return _with_rail(diagram)
    order = _chain(diagram)
    first = _place(diagram, order, {})
    return _with_rail(_place(diagram, order, _room(first, order)))


# Where the rail goes when the file does not say: the hero's 372 against
# its line at 150. A file with no node `at` still had to invent this one
# number, and a wrong one draws without a word.
RAIL_DROP = 222


def _with_rail(diagram):
    """The diagram with `rail.y` filled in if it was left out."""
    if diagram.rail is None or diagram.rail.y is not None:
        return diagram
    out = copy.deepcopy(diagram) if all(
        n.at is not None for n in diagram.nodes) else diagram
    ys = [n.at[1] for n in out.nodes if n.at is not None]
    out.rail.y = (max(ys) if ys else Y0) + RAIL_DROP
    return out


def _place(diagram, order, room):
    """A fresh copy placed along `order`, with `room[(a, b)]` for the
    pitch between two consecutive nodes where the habit's is too narrow."""
    out = copy.deepcopy(diagram)
    x = X0
    for rank, node_id in enumerate(order):
        node = out.node(node_id)
        if rank:
            # Up to the grid: geometry is on 10 px where practical, and a
            # solved file is read by people, who would rather see 470
            # than 461.03755.
            need = room.get((order[rank - 1], node_id), 0.0)
            x += max(PITCH, 10 * math.ceil(need / 10))
        if node.at is None:
            node.at = [x, Y0]
        else:
            x = node.at[0]
    _route_pairs(out)
    _place_sources(out, order)
    return out


def _room(placed, order):
    """How wide each run has to be for the labels on it, measured.

    `compose` returns the rectangle every label took. A node's label
    reaches some way into each run beside it — half its width each way when
    it sits above the node, all of it one way when `angle` or `side` put it
    beside the node, none the other. A branch's label sits centred on the
    run, so the run has to hold it with the larger of the two reaches on
    both sides: sized to the sum of two halves, 79 and 138 wide, the rack's
    technical-water label still overlapped by 5 on the wide side. A routed
    pair's label sits on the run's upper or lower leg, which is the run
    less a lead at each end, so it asks for that much more. The slack is
    the gap the label solver keeps between a block and a symbol, once at
    each end.
    """
    from ._layout import layout
    from ._render import compose
    placements = layout(placed)
    scene = compose(placements)
    width: Dict[str, float] = {}
    reach: Dict[str, float] = {}         # "left:id" / "right:id"
    for rect in scene.rects:
        owner = rect.owner
        if owner is None or not owner.ends:
            continue
        if owner.element == "node":
            node_x = owner.at[0]
            reach[f"right:{owner.ends[0]}"] = max(0.0, rect[0] + rect[2]
                                                  - node_x)
            reach[f"left:{owner.ends[0]}"] = max(0.0, node_x - rect[0])
        elif (owner.element in ("symbol", "anchor") and owner.role == "branch"
              and owner.copy in (None, 0) and owner.shown):
            key = f"branch:{owner.ends[0]}:{owner.ends[1]}"
            width[key] = max(width.get(key, 0.0), rect[2]
                             + (2 * LEAD if owner.via else 0.0))
    # A repeated branch's copies are boxes as well as a label: three in
    # series are longer than the habit's pitch on their own, and the
    # furnace wall's comb ran through both of its nodes at 220.
    span: Dict[str, List[float]] = {}
    for p in placements:
        if p.symbol is None or p.role != "branch" or not p.shown or p.via:
            continue
        key = f"branch:{p.ends[0]}:{p.ends[1]}"
        span.setdefault(key, []).extend(
            (p.at[0] - p.symbol.half_len, p.at[0] + p.symbol.half_len))
    for key, xs in span.items():
        width[key] = max(width.get(key, 0.0), max(xs) - min(xs) + 2 * LEAD)
    room: Dict[tuple, float] = {}
    for a, b in zip(order, order[1:]):
        between = max(width.get(f"branch:{a}:{b}", 0.0),
                      width.get(f"branch:{b}:{a}", 0.0))
        into = max(reach.get(f"right:{a}", 0.0), reach.get(f"left:{b}", 0.0))
        room[(a, b)] = between + 2 * into + 2 * SLACK
    return room


def _place_sources(diagram, order):
    """Every source without `at`, half a pitch out along its angle.

    An angle of 0 on a node that is not the hot end is turned first: a
    source arriving from the left onto an interior node arrives along the
    branch that is already there, so it comes from above instead, and one
    leaving to the right from an interior node leaves downward — heat in
    from the top and out to the cold head at the bottom, which is how run
    4's cryostat agent drew it, and which keeps an inbound and an outbound
    source on one node off each other. (Leaving *upward* put the outbound
    symbol above the node, on top of the inbound one.) The hot end keeps
    its source on the left, which is where the habit puts it, and a source
    leaving the cold end keeps going right.
    """
    below = {b.source for b in diagram.branches if b.target == M.RAIL} | \
        {b.target for b in diagram.branches if b.source == M.RAIL}
    above = set()
    for s in diagram.sources:
        if s.at is not None:
            continue
        node = diagram.node(s.node)
        rank = order.index(s.node)
        if s.angle == 0 and s.outward and rank != len(order) - 1:
            s.angle = 90
        elif s.angle == 0 and not s.outward and rank != 0:
            s.angle = 90
        rad = math.radians(s.angle)
        step = SOURCE if s.outward else -SOURCE
        s.at = [node.at[0] + math.cos(rad) * step,
                node.at[1] + math.sin(rad) * step]
        # Where the symbol landed, whoever chose the angle: the label rule
        # below cares about the lead, not about who turned it.
        if s.at[1] < node.at[1] - 1:
            above.add(s.node)
        elif s.at[1] > node.at[1] + 1:
            below.add(s.node)
    # A lead above and a wire below leave the node's label nowhere on the
    # line: above is the lead, below is the wire, and beside it is the run.
    # Diagonal clears all three, and since it was this pass that put the
    # source above, it is this pass that turns the label frame — only where
    # the author left it at its default, which is also 0. The wire below
    # is a capacitance to the rail, or a source this pass turned to leave
    # downward: the cryostat's shield had one of each in run 4 and its
    # label was reported adrift between them.
    for name in above & below:
        node = diagram.node(name)
        if node.angle == 0 and node.side == "auto":
            node.angle = 45


def _route_pairs(diagram):
    """Two branches between one pair of nodes, neither routed: one above,
    one below, and `side` to match where the author left it automatic.

    Both are drawn on the same straight run otherwise, which is a
    `symbols-overlap` error, and its remedy is exactly this. A third branch
    between the same pair keeps the straight run: a run has two useful
    sides, and the schema says so. A repeated branch cannot take `via` and
    is not counted.
    """
    pairs: Dict[frozenset, List[M.Branch]] = {}
    for b in diagram.branches:
        if M.RAIL in (b.source, b.target):
            continue
        pairs.setdefault(frozenset((b.source, b.target)), []).append(b)
    for members in pairs.values():
        # A repeated branch is a member — its comb takes the straight run —
        # but never routed, and its comb is what the plain ones go round.
        plain = [b for b in members if not b.repeated]
        if len(members) < 2 or not plain or any(b.via for b in plain):
            continue
        # A comb on the straight run has lanes either side of it, and 80
        # off the line does not clear four of them: the plain branch's box
        # sat on the outer lane. Its lanes are the same arithmetic `_form`
        # draws them with, so the leg goes that far out plus a box and a
        # gap, and never less than the habit.
        off: float = OFF
        for comb in members:
            if comb.repeated and comb.arrangement == "parallel":
                from ._layout import BRANCH_SYM, BY_KEY, PITCH_PAD
                half = BY_KEY[BRANCH_SYM.get(comb.kind, comb.kind)].half
                copies = comb.count or 1
                lanes = (copies - 1) * (2 * half + PITCH_PAD) / 2 + half
                off = max(off, lanes + 2 * half)
        legs = (("up", -1), ("down", 1))
        # One plain branch round a comb makes a loop, and the comb's own
        # label above it sat inside that loop, close to both paths —
        # `label-in-a-corridor`. The comb's label goes the other way.
        if len(plain) == 1:
            for comb in members:
                if comb.repeated and comb.side == "auto":
                    comb.side = "down"
        for b, (side, sign) in zip(plain, legs):
            (xa, ya), (xb, yb) = (diagram.node(b.source).at,
                                  diagram.node(b.target).at)
            step = LEAD if xb >= xa else -LEAD
            level = (min(ya, yb) if sign < 0 else max(ya, yb)) + sign * off
            b.via = [[xa + step, ya], [xa + step, level],
                     [xb - step, level], [xb - step, yb]]
            if b.side == "auto":
                b.side = side
